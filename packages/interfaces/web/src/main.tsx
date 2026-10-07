import { render } from "preact";
import "@picocss/pico/css/pico.min.css";
import "./styles.css";
import { App } from "./App";
import { connect } from "./api/socket";
import { bindHotkeys } from "./hotkeys";

connect();
bindHotkeys();
render(<App />, document.getElementById("app")!);
