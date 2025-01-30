# InitVerse Bot
⚠️ The script have been Revamped for mainnet Tasks

If you find this library useful, consider starring this repository⭐️

A Python-based bot for interacting with the InitVerse mainnet. Automate task like performing trades and completing additional periodic twitter tasks.

## Getting Started

### Prerequisites

1. **Create an Account on InitVerse**
   - Visit [InitVerse Candy](https://candy.inichain.com/) and connect your wallet.
   - Link your social accounts and complete the "Start Here" task.
   - Join the [miner pool](https://inichain.gitbook.io/initverseinichain/inichain/mining-mainnet) with the operating system of your choice(Windows/Linux).
   - Get INI token by mining or receiving from someone.

### Setup

Follow the steps below to set up and run the bot.

#### 1. Clone the Repository
```bash
git clone https://github.com/Anzywiz/InitVerse-bot.git
cd InitVerse-bot
```

#### 2. Create and Activate a Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configuration
   - Create a `config.json` file in the project directory with the following structure:
     ```json
     {
       "private_keys": ["private_key1", "private_key2"]
     }
     ```
   - Replace `private_key1` and `private_key2` with your private keys.

#### 4. Run the Bot
```bash
python main.py
```

## Features

- Automates daily check-ins
- Token swapping
- Interacts with the InitVerse testnet
- Periodically performs additional tasks

## Issues
If you enconter any issues, please do let me know in [issues]()

## License

This project is licensed under the MIT License.
