# python-lsp-server-docker

This repository is a dockerfile that builds a docker image of the python language server using LSP protocol.

python-lsp-server can be found here : https://github.com/python-lsp/python-lsp-server

# Running LSP server container

1. Build the container with `docker build -t python-lsp-server .`
2. Start the container with `docker run -p 8080:8080 python-lsp-server`

The websocket url should be running at ws://localhost:8080

# Demo project

In the demo-project subfolder, there is a simple react app that you can use to test the websocket URL of the container.
To run the demo project, cd into the demo-project folder, install the dependencies with `npm install` then `npm start` to start the app. In App.js, change the const serverUri to the websocket uri which should be on port 8080.

# Current status

- All functionalties work except lint on button click
