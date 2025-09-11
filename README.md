# AI Negotiation Agent

### An AI-powered buyer agent for a technical interview project.

This project implements an autonomous negotiation agent designed to secure profitable deals on perishable goods. The agent's core function is to negotiate against a hidden seller, demonstrating a consistent personality and a robust strategy to achieve maximum savings within strict budget constraints and a limited number of negotiation rounds.

-----

### Key Features

  * **Intelligent Negotiation**: Employs a strategic approach to offers and counteroffers.
  * **Personality-Driven Logic**: Maintains a consistent character throughout all negotiations, influencing its negotiation style and messaging.
  * **Budget Management**: Never exceeds the defined budget, ensuring all deals are profitable.
  * **Deadline Awareness**: Adapts its strategy as the negotiation approaches a timeout, prioritizing deal completion.

-----

### Core Components

The agent is built with a modular design, with each component handling a specific aspect of the negotiation process.

  * **Personality Component**: Defines the agent's character traits, negotiation style, and tone (e.g., "aggressive," "diplomatic," "analytical").
  * **Memory Component**: Tracks the complete history of all offers and messages from both the buyer and the seller.
  * **Observation Component**: Parses incoming messages to extract key information, such as the seller's current price.
  * **Decision Component**: The "brain" of the agent, using all available information to decide whether to accept an offer, make a counteroffer, or walk away.

-----

### Getting Started

#### 1\. Clone the repository

```bash
git clone [repository-url]
cd [repository-folder]
```

#### 2\. Set up a virtual environment

This ensures project dependencies are isolated.

  * **Windows:**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
  * **macOS/Linux:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

#### 3\. Install Dependencies

```bash
pip install -r requirements.txt
```

-----

### How to Run

To test your agent, run the main script from the terminal.

1.  Navigate to the `interviewTask` directory within your project folder:
    ```bash
    cd interviewTask
    ```
2.  Execute the main script:
    ```bash
    python interview_negotiation_template.py
    ```

The script will run your agent through a series of automated test scenarios and print a summary of its performance, including deal success rate and total savings.

-----

### Agent Design

My agent is designed with an **analytical** personality. This approach is based on a clear, data-driven strategy.

  * **Opening Offer**: The agent calculates its first offer as a percentage of the market price, adjusted for product quality. This provides a strong starting point and justifies its position with a logical argument.
  * **Dynamic Concession Strategy**: Instead of making random offers, the agent uses a tiered concession rate. It makes small, careful concessions early in the negotiation but becomes more flexible as the deadline approaches to ensure a deal is reached.

This combination of a consistent personality and a robust, data-backed strategy makes the agent both effective and reliable.
