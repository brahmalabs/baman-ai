# BamanAI

BamanAI is an open-source platform that empowers tutors and educational institutes to create, train, and deploy custom AI assistants across multiple channels.

## Features

- **Custom AI Assistants**: Create and train AI models tailored to your educational content.
- **Multi-Channel Deployment**: Deploy your assistants on WhatsApp, Telegram, Instagram, Facebook, and a web application.
- **24/7 Student Support**: Provide round-the-clock assistance to students.
- **Open Source**: Built with Python, allowing for community contributions and improvements.
- **CRM Integration**: Seamlessly integrate with existing school CRM systems.

## Demo

You can try out the demo of BamanAI [here](https://bamanai.brahma-labs.com/).
Watch the demo video [here](https://youtu.be/fObyWPQzLus).

## Getting Started

### Prerequisites

- Python 3.8+
- pip
- Virtual environment (recommended)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/brahma-labs/bamanai.git
   cd bamanai
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your specific configurations
   ```

5. Run the application:
   ```bash
   python app.py
   ```

## Platform Integration

To integrate WhatsApp and Telegram with BamanAI, tutors and institutes need to obtain access keys from their respective developer consoles:

1. **WhatsApp**: Obtain API credentials from the Meta for Developers console.
2. **Telegram**: Create a bot and get the API token from the BotFather.

Once you have the necessary access keys, update them in the BamanAI dashboard to connect your channels.

For detailed integration instructions, please refer to our [Integration Guide](docs/integration-guide.md).

## Usage

1. **Create an Assistant**: Use the web interface to create and train your custom AI assistant.
2. **Deploy**: Choose the platforms where you want to deploy your assistant.
3. **Integrate**: Follow our guide to integrate BamanAI with your existing CRM system.
4. **Monitor**: Track usage and improve your assistant's performance over time.

## Contributing

We welcome contributions from the community! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to submit pull requests, report issues, and suggest improvements.

## Support

For additional support, customization, and integration services, please contact us at admin@brahma-labs.com.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## About Brahma Labs

BamanAI is developed by [Brahma Labs](https://brahma-labs.com) as an open-source experiment in educational technology. We're committed to advancing AI-powered learning experiences.

---

Star ⭐ this repo if you find it useful! Issues and pull requests are welcome.
