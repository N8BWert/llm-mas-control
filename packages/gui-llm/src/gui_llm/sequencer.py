"""
Since the engine has no completion acks, this sequencer manages actions above GUI.agent_action_queue.

The sequencer decides when an action is done (falling edge or 10 tick idle latch),
then it empties the "queue" and inserts one next action.
"""

from dataclasses import dataclass

from common.agent_action import AgentAction
from common.game_state import GameState
from gui_llm.parsing import cmd_id

# Absorb engine latency by having some ticks of tolerance before interpreting idle as idle.
IDLE_TICKS_DONE: int = 10


@dataclass
class Program:
    """
    One ant's commands.
    """
    steps: list[AgentAction]
    pc: int = 0                    # Index of the active step
    loop_start: int | None = None  # When pc runs off the end, jump here; None means no loop
    seen_busy: bool = False        # Whether the ant has been seen busy since the active step was dispatched
    idle_ticks: int = 0            # Consecutive idle ticks since the active step was dispatched

    @property
    def looping(self) -> bool:
        return self.loop_start is not None

    def restart_watch(self):
        self.seen_busy = False
        self.idle_ticks = 0

    def advance(self):
        """
        Moves to the next step, wrapping into the loop body if there is one.
        """
        self.pc += 1
        if self.pc >= len(self.steps) and self.looping:
            self.pc = self.loop_start
        self.restart_watch()

    def finished(self) -> bool:
        return self.pc >= len(self.steps)

    def view(self) -> list[AgentAction]:
        """
        Returns:
            The remaining steps, active one first. A looping program shows one full pass.
        """
        if self.finished():
            return []
        rest = self.steps[self.pc:]
        if self.looping and self.pc > self.loop_start:
            rest += self.steps[self.loop_start:self.pc]
        return rest


class Sequencer:
    def __init__(self, num_agents: int = 10):
        self.programs: list[Program | None] = [None] * num_agents

    # Editing programs
    def replace(self, agent_id: int, actions: list[AgentAction], loop: bool):
        self.programs[agent_id] = Program(list(actions), loop_start=0 if loop else None) if actions else None

    def append(self, agent_id: int, actions: list[AgentAction], loop: bool):
        old = self.programs[agent_id]
        if old is None or old.finished():
            self.replace(agent_id, actions, loop)
            return
        # A looping program finishes its current pass, then runs the new steps
        # Rebase the program so its current pass is laid out in order from pc
        steps = old.view()
        program = Program(
            steps + list(actions),
            pc=0,
            loop_start=len(steps) if loop else None,
            seen_busy=old.seen_busy,
            idle_ticks=old.idle_ticks,
        )
        self.programs[agent_id] = program

    def cancel_all(self, agent_id: int):
        self.programs[agent_id] = None

    def cancel_current(self, agent_id: int):
        program = self.programs[agent_id]
        if program is not None and not program.finished():
            program.advance()
            self._drop_if_done(agent_id)

    def cancel_ids(self, agent_id: int, cmd_ids: list[str] | set[str]):
        program = self.programs[agent_id]
        if program is None or program.finished():
            return
        cmd_ids = set(cmd_ids)
        active = program.steps[program.pc]
        kept, pc, loop_start = [], None, None
        for i, step in enumerate(program.steps):
            if program.looping and i == program.loop_start:
                loop_start = len(kept)
            if i == program.pc:
                pc = len(kept)  # The next kept step at or after the active one
            if cmd_id(step) not in cmd_ids:
                kept.append(step)
        if program.looping and loop_start is not None and loop_start >= len(kept):
            loop_start = None  # The whole loop body was cancelled
        program.steps, program.pc, program.loop_start = kept, pc, loop_start
        if program.pc >= len(kept) and program.looping:
            program.pc = program.loop_start
        if program.finished() or program.steps[program.pc] is not active:
            program.restart_watch()
        self._drop_if_done(agent_id)

    # Running programs
    def update(self, game_state: GameState):
        """
        Call once per tick. Advances every ant whose active command looks done.
        """
        busy = {agent.id: agent.busy for agent in game_state.agent_states}
        for agent_id, program in enumerate(self.programs):
            if program is None:
                continue
            if agent_id not in busy:  # Dead or respawning; the base GUI clears its queue too
                self.programs[agent_id] = None
                continue
            if busy[agent_id]:
                program.seen_busy = True
                program.idle_ticks = 0
                continue
            program.idle_ticks += 1
            # Advance at once on a busy->idle edge, or the engine restarts the finished action
            if program.seen_busy or program.idle_ticks >= IDLE_TICKS_DONE:
                program.advance()
                self._drop_if_done(agent_id)

    def view(self, agent_id: int) -> list[AgentAction]:
        program = self.programs[agent_id]
        return [] if program is None else program.view()

    def looping_ids(self) -> set[int]:
        """
        Returns:
            The id() of every action inside a loop body.
        """
        return {
            id(step)
            for program in self.programs
            if program is not None and program.looping
            for step in program.steps[program.loop_start:]
        }

    def sync(self, queues: list[list[AgentAction]]):
        """
        Mirrors the programs into the GUI's queues. Only queue[0] is ever published to the engine.
        """
        for agent_id in range(len(self.programs)):
            queues[agent_id][:] = self.view(agent_id)

    def _drop_if_done(self, agent_id: int):
        program = self.programs[agent_id]
        if program is not None and program.finished():
            self.programs[agent_id] = None
