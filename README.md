# Trading Assistant

This is a Python-based trading assistant that interacts with Interactive Brokers via the `ib_insync` library. It collects user input, fetches options data, and executes trades based on predefined strategies. Please note, this is meant to be used for Paper Trading only. If you use this code with a live account, you're responsible for any losses that occur.

---

## 📦 Requirements

- Python 3.8 or higher
- `pip` (Python package installer)

---

## 🛠️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

### 3. Activate the Virtual Environment

- on MacOS/Linux:

```bash
source venv/bin/activate
```

- on Winblows:

```bash
source venv/bin/activate
```

#### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 🚀 Running the Application

```bash
python main.py
```

This will start the trading assistant, prompt for user input, and begin the trading logic.

---

### 📁 Logs

Logs are saved in the logs/ directory, with one log file per traded symbol.

---

### 🧾 License

This project is licensed under the MIT License.
