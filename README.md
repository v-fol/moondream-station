<div>
   <p align="center">
   <img src="assets/md_logo_clean.png" alt="Moondream Station Logo" width="200"/>
   </p>

   <h3 align="center"><strong>Moondream Station: 100% free local visual reasoning</strong></h3>

   <p align="center">
      <a href="https://moondream.ai/station" target="_blank"><img src="https://img.shields.io/badge/Home-%F0%9F%8F%A0-blue?style=flat-square" alt="Home Page"></a>
      <a href="https://discord.gg/QTaWPdDZ" target="_blank"><img src="https://img.shields.io/badge/Discord-5865F2?logo=discord&logoColor=white&style=flat-square" alt="Discord"></a>
      <a href="https://x.com/moondreamai" target="_blank"><img src="https://img.shields.io/badge/follow-%40moondreamai-000000?style=flat-square&logo=x&logoColor=white" alt="Follow @moondreamai"></a>
      <a href="LICENSE" target="_blank"><img src="https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square" alt="License"></a>
   </p>
</div>

<hr style="height:3px;border:none;background:#e0e0e0;margin:24px 0;">

<table align="center">
<tr>
<td width="420" align="center" valign="middle">

<!-- Demo video -->
![Video showing Moondream Station running in a terminal](assets/md_station_demo.gif)

</td>
<td width="400" align="left" valign="middle">

### How It Works

🚀 **Launches Local Server**  
   All inference runs on your device

🔧 **Control via CLI**  
   Caption images, answer questions, and manage settings

🌐 **Access via HTTP**  
   Connect to `http://localhost:2020/v1` through REST or our [Python](https://pypi.org/project/moondream/), [Node](https://www.npmjs.com/package/moondream), or [OpenAI](https://github.com/openai/openai-python) client

</td>
</tr>
</table>

## Installation

```bash
pip install -e .
```

## Usage

```bash
moondream-station
```

## Commands

### Model Management
- `models` - List available models
- `models switch <model>` - Switch to a model

### Service Control
- `start [port]` - Start REST server (default: port 2020)
- `stop` - Stop server
- `restart` - Restart server

### Inference
<img width="522" height="376" alt="Screenshot 2025-09-12 at 8 59 09 PM" src="https://github.com/user-attachments/assets/855d10b6-fb95-4731-9fbd-ce7cc46e78a3" />

- `infer <function> [args]` - Run single inference
- `inference` - Enter interactive inference mode

### Settings
<img width="516" height="362" alt="Screenshot 2025-09-12 at 9 01 57 PM" src="https://github.com/user-attachments/assets/696189b2-b8cc-4785-88a2-cb11f805668f" />

- `settings` - Show configuration
- `settings set <key> <value>` - Set setting value

### Utility
<img width="503" height="225" alt="Screenshot 2025-09-12 at 9 01 08 PM" src="https://github.com/user-attachments/assets/486780e1-08c6-46d4-bebb-77aadd1ca73b" />

- `session` - Show session stats
- `help` - Show available commands
- `history` - Show command history
- `clear` - Clear screen
- `exit` - Quit application

## REST API

Once a model is running, HTTP requests are routed to backend functions:

```bash
# Start server
start

# Make requests
curl -X POST http://localhost:2020/v1/caption \
  -H "Content-Type: application/json" \
  -d '{"image_url": "data:image/jpeg;base64,...", "length": "short"}'

curl -X POST http://localhost:2020/v1/query \
  -H "Content-Type: application/json" \
  -d '{"image_url": "data:image/jpeg;base64,...", "question": "What is this?"}'
```

Available endpoints depend on the loaded model backend.

## Configuration

Settings are stored in `~/.moondream-station/config.json`. Key settings:

- `inference_workers` - Number of concurrent workers (default: 2)
- `inference_timeout` - Request timeout in seconds (default: 60)
- `auto_start` - Auto-start server when model selected (default: true)
- `service_port` - Default server port (default: 2020)
