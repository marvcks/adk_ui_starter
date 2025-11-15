# UI for Google-ADK

## npm install
```bash
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
# restart shell
nvm install node
```
## python environment

```bash
pip install google-adk mcp litellm dotenv arxiv
```

## clone repository
```bash
cd /root
git clone https://github.com/marvcks/adk_ui_starter.git
cd adk_ui_starter/ui
npm install
cd adk_ui_starter
./start-agent-prod.sh
# open http://localhost:50001
``

## Setup

1. example_agent/.env
2. .env.example
3. config/agent-config.json
4. ui/src/components/ChatInterface.tsx line 600-657.

