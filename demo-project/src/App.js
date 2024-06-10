import React, { useEffect, useRef, useState } from "react";
import { EditorView } from "codemirror";
import { EditorState } from "@codemirror/state";
import {
  languageServer,
  LanguageServerClient,
} from "codemirror-languageserver";
import { basicSetup } from "codemirror";
import { python } from "@codemirror/lang-python";
import { lintGutter } from "@codemirror/lint";
import { indentationMarkers } from "@replit/codemirror-indentation-markers";

function App() {
  const editor = useRef(null);
  const viewRef = useRef(null);

  const serverUri = "ws://localhost:8080";
  const rootUri = "file:///home/";
  const documentUri = `${rootUri}index.py`;

  useEffect(() => {
    // const newClient = new LanguageServerClient({
    //   serverUri,
    //   rootUri,
    // });

    const ls = languageServer({
      serverUri,
      rootUri,
      // client: newClient,
      documentUri,
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
    };
  }, []);

  const handleFormatCode = async () => {
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

    // const response = await lsClient.textDocumentFormat(formatRequest);
    // if (response.id === 1 && response.result) {
    //   const formatted = response.result[0].newText;
    //   editorView.dispatch({
    //     changes: {
    //       from: 0,
    //       to: doc.length,
    //       insert: formatted,
    //     },
    //   });
    // }
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
