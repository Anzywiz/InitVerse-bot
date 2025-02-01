
# InitVerse Mainnet Bot  

⚠️ **The script previously for the testnet tasks has been revamped for mainnet tasks!**  

If you find this library useful, please consider starring this repository ⭐️  

A Python-based bot for interacting with the InitVerse mainnet. Automates tasks like performing trades and completing periodic Twitter tasks.  

## Getting Started  

### Prerequisites  

1. **Create an Account on InitVerse**  
   - Visit [InitVerse Candy](https://candy.inichain.com/) and connect your wallet.  
   - Link your social accounts and complete the "Start Here" task.  
   - Join the [miner pool](https://inichain.gitbook.io/initverseinichain/inichain/mining-mainnet) with the operating system of your choice (Windows/Linux).  
   - Acquire INI tokens by mining or receiving them from someone.  

### Setup  

Follow these steps to set up and run the bot.  

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

#### 4. Configure the Bot  
Create a `config.json` file in the project directory with the following structure:  
```json
{
  "private_keys": ["your_private_key1", "your_private_key2"]
}
```
Replace `your_private_key1` and `your_private_key2` with your actual private keys.  

#### 5. Run the Bot  
```bash
python main.py
```

## Features  

- Automated daily trading  
- Periodic Twitter tasks  


## Issues & Contributions  

If you encounter any issues, please report them in the [Issues section](https://github.com/Anzywiz/InitVerse-bot/issues).  

💡 Want to improve the bot? Fork the repository, make your changes, and submit a pull request (PR)! Contributions are always welcome.  
 

This project is licensed under the MIT License.  

⭐ **Don't forget to star the repo if you find it useful!** Your support keeps it growing! 😊  

---
