# Contributing to DRASTIC-Tox

First — thank you for considering contributing! 🎉

DRASTIC-Tox is a research-oriented tool for groundwater risk assessment in Sudanese mining areas. We welcome contributions from hydrogeologists, data scientists, and developers.

---

## 🎯 How to Contribute

### 1. Report Bugs
Open an [Issue](https://github.com/USERNAME/smart-mining-app/issues) with:
- **Description** of the bug
- **Steps** to reproduce
- **Screenshot** (if applicable)
- **Environment** (browser, OS)

### 2. Suggest Features
Open an [Issue](https://github.com/USERNAME/smart-mining-app/issues) with label `enhancement`:
- **Use case** description
- **Expected** behavior
- **Scientific** justification (if applicable)

### 3. Submit Code
1. Fork the repository
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m "Add: your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a **Pull Request**

### 4. Contribute Data
If you have groundwater data from Sudan/Africa:
- Contact us at **Shihabalhadi16@gmail.com**
- We'll credit you in the paper

---

## 📋 Code Guidelines

### Python Style
- **PEP 8** compliant
- Max line length: **100 characters**
- Use **type hints** where possible
- Docstrings: **Google style**

### Streamlit Widgets
- Always use **unique `key=`** for widgets
- Add `help=` text for complex inputs
- Test on **both AR and EN**

### Scientific Code
- Cite **references** in docstrings
- Validate against **known results**
- Add **unit tests** for calculations

### Protected Files (DO NOT MODIFY)
- `data_sources.py` — contains verified field data
- `weights/weights_config.json` — user configuration

---

## 🌍 Language

- Code comments: **English**
- UI strings: **Arabic + English** via `translations.py`
- Documentation: **English** primary

---

## 🧪 Testing

Before submitting:
```bash
streamlit run app.py
# Test all 17 tabs
# Test AR/EN switching
# Test file upload
