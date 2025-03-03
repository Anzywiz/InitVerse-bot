# InitVerse Mainnet Bot 🚀

⚠️ **The script has been revamped for mainnet tasks!**

If you find this project useful, please consider starring the repository ⭐️

A Python-based bot for interacting with the InitVerse mainnet. It automates tasks such as performing trades, completing periodic Twitter tasks, and supporting multi-account farming with proxy integration.

## 🔰 Getting Started

### ✅ Prerequisites

1. **Create an Account on InitVerse**  
   - Visit [InitVerse Candy](https://candy.inichain.com/) and connect your wallet.
   - Link your social accounts and complete the "Start Here" task.
   - Join the [miner pool](https://inichain.gitbook.io/initverseinichain/inichain/mining-mainnet) using Windows or Linux.
   - Acquire INI tokens by mining or receiving them from someone.

### ⚙️ Setup

Follow these steps to set up and run the bot.

#### 📂 1. Clone the Repository
```bash
git clone https://github.com/Anzywiz/InitVerse-bot.git
cd InitVerse-bot
```

If you have previously set up the script, update it with:
```bash
git pull
pip install -r requirements.txt
```

#### 🖥️ 2. Create and Activate a Virtual Environment

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

#### 📦 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### ⚙️ 4. Configure the Bot
Create a `config.json` file in the project directory with the following structure:
```json
{
  "private_keys": ["your_private_key1"],
  "timeout_between_trades_in_sec": 10,
  "timeout_after_trades_in_hrs": 12,
  "send_amount": 0.000001,
  "proxies": null
}
```
Replace `your_private_key1` with your actual private key. You can add multiple private keys to enable multi-account trading.

#### ▶️ 5. Run the Bot
```bash
python main.py
```

## ✨ Features

- 🤖 Automated daily trading
- 🐦 Periodic Twitter tasks
- 🔄 Multi-account trading/farming
- 🛡️ Proxy support for enhanced security and anonymity

## 🛠️ Issues & Contributions

If you encounter any issues, please report them in the [Issues section](https://github.com/Anzywiz/InitVerse-bot/issues).

💡 Want to contribute? Fork the repository, make your changes, and submit a pull request (PR). Contributions are always welcome!

## 📜 License

This project is licensed under the MIT License.

⭐ **Support the project by starring the repo!** 😊

