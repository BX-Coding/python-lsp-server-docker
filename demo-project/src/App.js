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
    const serverUri = "ws://localhost:8080";

    wsRef.current = new WebSocket(serverUri);

    const ls = languageServer({
      serverUri,
      rootUri: "file:///home/",
      documentUri: "file:///home/index.py",
      languageId: "python",
      workspaceFolders: [
        {
          uri: "file:///home/",
          name: "root",
        },
      ],
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

  const handleFormatCode = async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error("WebSocket is not open. Cannot send formatting request.");
      return;
    }

    const editorView = viewRef.current;
    const doc = editorView.state.doc.toString();

    const formatRequest = {
      jsonrpc: "2.0",
      id: 1,
      method: "textDocument/formatting",
      params: {
        textDocument: {
          uri: "file:///home/index.py",
        },
        options: {
          tabSize: 4,
          insertSpaces: true,
        },
      },
    };

    wsRef.current.send(JSON.stringify(formatRequest));

    wsRef.current.onmessage = (event) => {
      const response = JSON.parse(event.data);
      if (response.id === 1 && response.result) {
        const formatted = response.result[0].newText;
        editorView.dispatch({
          changes: {
            from: 0,
            to: doc.length,
            insert: formatted,
          },
        });
      } else if (response.error) {
        console.error("Error in formatting response:", response.error);
      }
    };

    wsRef.current.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    wsRef.current.onclose = (event) => {
      console.warn("WebSocket closed:", event);
    };
  };

  return (
    <div className="App">
      <h1>Python Code Editor</h1>
      <button onClick={handleFormatCode}>Format Code</button>
      <div ref={editor}></div>
    </div>
  );
}

export default App;
