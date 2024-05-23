import React, { useEffect, useRef } from "react";
import { EditorView } from "codemirror";
import { EditorState } from "@codemirror/state";
import { languageServer } from "codemirror-languageserver";
import { basicSetup } from "codemirror";
import { python } from "@codemirror/lang-python";
import { lintGutter } from "@codemirror/lint";
import { indentationMarkers } from "@replit/codemirror-indentation-markers";

function App() {
  const editor = useRef(null);

  useEffect(() => {
    const serverUri = "ws://localhost:8000";

    const ls = languageServer({
      serverUri,
      rootUri: "file:///",
      documentUri: "file:///index.js",
      languageId: "python",
    });

    const startState = EditorState.create({
      doc: "# Write your Python code here",
      extensions: [
        basicSetup,
        ls,
        python(),
        lintGutter(),
        indentationMarkers(),
      ],
    });

    const view = new EditorView({
      state: startState,
      parent: editor.current,
    });

    return () => {
      view.destroy();
    };
  }, []);

  return (
    <div className="App">
      <h1>Python Code Editor</h1>
      <div ref={editor}></div>
    </div>
  );
}

export default App;
