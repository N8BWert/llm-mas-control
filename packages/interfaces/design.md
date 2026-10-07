# Basic Requirements
## Testing
* Dummy data
* Game rules
  * X number of robots (configurable)
  * Robots have X speed
  * Robots get to a location and do a timed action
  * 2D playfield
  * Robot behavior: do nothing until commanded
* Constraints
## Frontend
### Information
- Display game information: current score and remaining time.
- Show a map that includes robot positions, terrain features, enemy locations, resources, objectives, and a live video stream.
- Present each robot’s current intent and goals:
  - Destination/current path
  - Current and upcoming actions
  - Time remaining for ongoing tasks
- Selected group panel displays:
  - Number of robots selected
  - Associated objectives
- Display robot/swarm states including:
  - Health
  - Availability
  - Current action
  - Selection status
  - Critical failures (e.g., constraint violations)
- Use distinguishable color schemes:
  - All friendly robots are blue; roles are represented by different blue shades.
- Clearly indicate any constraints and highlight violations.
### User Actions
- Robot selection options:
  - Single-click to select a robot
  - Shift/ctrl + click for multi-selection
  - Click and drag to box-select multiple robots
  - Click again to deselect robots
- Issue commands to selected robots
- Access emergency controls: stop all actions, initiate retreat
## Backend
- Provide real-time video streaming capabilities.
- Establish a connection with the server to exchange information (sending and receiving).
- Parse incoming data from robots.
- Format and send outgoing commands to robots.
- Manage and update game state using structured objects.
- Serve a responsive Web UI to users.
- Integrate with an LLM for command processing or state interpretation.
- Convert game and robot state information into formats readable by the LLM.
- Implement various hooks, methods, and interfaces for seamless integration with the underlying engine.
# RTS Interface
## Additional Requirements
### User Actions
- Give commands: set waypoint, draw path, click to action location (ex: mine here, robot automatically navigates)
# LLM Interface
## Information
- Strategy panel
- Command queue: which commands are waiting, in work, completed 
## User Actions
- Give overarching strategy
