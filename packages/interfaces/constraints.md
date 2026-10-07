# Constraints
Throughout the game/between rounds of the game, a random constraint will be imposed on the user’s swarm. Violating the constraint will result in a steep penalty to the user to simulate non-trivial consequences of a fielded robot system. 

## Unanswered questions:
- 1 constraint per round? 
- Varying constraints
    - For a single person, between RTS rounds and LLM rounds, should we do different or same constraints? 
    - Between people, should we do different or same constraints? 
    - The thing that would produce the cleanest data is keeping the same constraints between RTS rounds and LLM rounds, and between people. 
- Should we change the difficulty of the constraints?
    - I think yes, but how that’s done, idk. Maybe start with no constraint, then simple, then hard.
    - This possibly depends on the pace of the game. If it’s a slow game (aka the robots are super slow), then 2 min isn’t a lot of time to get data on a person’s quality of play before changing the rules. 

## Types of Constraints
Each time a robot violates a constraint, points are lost.

### Zone Constraints
- **Restricted Zones (Easy):** Define one or more areas on the map that robots are prohibited from entering.
  - _Scaling difficulty:_ Enlarge restricted zones, increase the number of prohibited areas, or position them over critical locations.
- **Timed Entry Zones (Medium):** Robots may only enter certain areas for a limited duration before having to exit (e.g., hazard zones).
  - _Example:_ Radiation or hazard area that damages robots if overstayed.
  - _Scaling difficulty:_ Larger zones, multiple timed zones, or placement over high-value regions.
- **Occupation Zones (Easy):** At least one friendly robot must continuously occupy specified zones at all times.
  - _Note:_ May be less challenging in some scenarios (e.g., initial assignment suffices), but smaller or strategically important zones increase difficulty.
  - _Scaling difficulty:_ Reduce zone size or require occupation of more significant/contested areas.
- **Overwatch Requirement (Hard):** Specific zones require a friendly robot to maintain an overwatch position as a prerequisite for other robots to access adjacent regions.
- **Critical Waypoint Deadline (Hard):** A friendly robot must reach a designated waypoint within a fixed time interval to ensure a crucial game event (e.g., secure a supply drop before it’s intercepted by the enemy).

### Time Constraints
- **Deadline Tasks:** A specific task must be completed within a set timeframe; failing to do so results in a penalty. 
  - _Design note:_ This constraint may be difficult to balance, as tasks are either completed in time or not, potentially yielding limited insight unless carefully tuned.
- **Limited Activity Interval (Medium):** Each robot may remain active for only a defined duration before it must return to base to “refuel” or “refresh” prior to redeployment.
  - _Design note:_ This constraint becomes more interesting and challenging when used in combination with other constraints, such as in overwatch or zone-holding scenarios.

### Numeric Constraints
- **Participation Limit (Easy):** Only a specified subset of robots may participate in certain tasks or missions; others must remain inactive or in reserve.
- **Minimum Requirement (Hard):** A task or action requires at least a set number of robots to be performed successfully (e.g., at least 3 robots must cooperate to retrieve a highly valuable resource).
  - _Example:_ Retrieving a high-value resource that cannot be collected unless enough robots are involved.

### Contact Constraints
- **Avoid Contact (Hard):** Robots must avoid coming into contact with designated game elements, such as enemy robots.  
  - _Note:_ This constraint only applies when enemy robots or specific hazardous elements are present in the scenario.
- **Maintain Contact (Medium):** Robots are required to maintain physical contact with another friendly robot while completing a given task.
  - _Example:_ Two robots must stay linked together while moving or performing a joint action; breaking contact incurs a penalty.

### Protection Constraints 
- **Protection Objective (Hard):** A specific friendly robot must remain unharmed for the duration of the round or until a particular mission objective is met; if this robot is destroyed or incapacitated, the task is failed.
  - _Note:_ This constraint applies only when enemy robots or hostile entities are actively present in the game scenario.

### Heterogeneous Constraints
**Role-Specific Constraints (Medium):** Assign distinct roles to certain robots, such that only robots with a specific role can perform particular tasks or subtasks.
  - _Scaling difficulty:_ Reduce the number of robots available with key (bottleneck) roles, making it more challenging to accomplish all required tasks.
  - _Design note:_ If the number of robots in essential roles becomes too low, overall game progress may slow significantly, leading to increased idle time and potential frustration regardless of interface.
