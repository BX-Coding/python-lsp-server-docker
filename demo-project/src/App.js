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
  const viewRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    const serverUri = "ws://localhost:8000";

    wsRef.current = new WebSocket(serverUri);

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

    viewRef.current = view;

    return () => {
      view.destroy();
      wsRef.current.close();
    };
  }, []);

  const lintCode = () => {
    if (wsRef.current && viewRef.current) {
      const code = viewRef.current.state.doc.toString();

      const lintRequest = {
        jsonrpc: "2.0",
        id: 1,
        method: "textDocument/formatting",
        params: {
          textDocument: {
            uri: "file:///index.js",
            text: code,
          },
        },
      };

      // console.log("Lint request:", JSON.stringify(lintRequest));
      wsRef.current.send(JSON.stringify(lintRequest));
      wsRef.current.addEventListener("message", (event) => {
        console.log("Lint response:", event.data);
      });
    }
  };

  return (
    <div className="App">
      <h1>Python Code Editor</h1>
      <div ref={editor}></div>
      <button onClick={lintCode}>Lint Code</button>
    </div>
  );
}

export default App;
