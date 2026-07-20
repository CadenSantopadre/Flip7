# Flip 7 Analysis
*A statistical analysis and simulation toolkit for optimizing Flip 7 strategy.*

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Simulation](https://img.shields.io/badge/Monte%20Carlo-Enabled-green)
![Status](https://img.shields.io/badge/Status-Done-green)

---

## Overview

Flip 7 Analysis is a Python application that uses large-scale Monte Carlo simulations to determine the optimal strategy for the card game **Flip 7**.

Instead of relying on intuition, the program simulates hundreds of thousands of games to evaluate expected value, winning probability, and optimal stopping strategies against different types of opponents.

The goal is to answer one question:

> **When should you stop flipping cards to maximize your chance of winning?**

---

## Features

### 📊 Expected Value Analysis

Calculates the expected value (EV) of continuing to flip versus stopping.

Displays:

- Current score
- Expected score gain
- Bust probability
- Risk vs. reward
- Optimal decision

---

### 🎲 Monte Carlo Simulation

Runs hundreds of thousands of simulated Flip 7 games.

Features:

- Adjustable simulation count
- Fast statistical analysis
- Confidence estimates
- Average game statistics
- Distribution of outcomes

The large sample size allows the strategy recommendations to converge toward the true probabilities.

---

### 🏆 Win Rate Calculator

Measures the probability of winning using different strategies.

Compares:

- Conservative play
- Aggressive play
- Fixed stopping thresholds
- Adaptive strategies
- AI-generated strategies

Results include:

- Win percentage
- Average score
- Bust frequency
- Expected placement

---

### 🤖 Human Player Simulation

Simulates opponents with realistic decision-making rather than perfect play.

Configurable behaviors include:

- Risk tolerance
- Greedy players
- Conservative players
- Random players
- Adaptive players

This allows strategies to be optimized against real-world opponents instead of theoretical ones.

---

### 🎯 Optimal Stopping Strategy

Determines the best point to stop drawing cards based on simulation data.

The program evaluates:

- Current score
- Remaining deck state
- Number of opponents
- Opponent behavior
- Probability of busting
- Expected future value

Outputs the statistically optimal decision at every stage of the game.

---

### 📈 Statistical Dashboard

Visualizes simulation results with interactive charts.

Includes:

- Win rate data
- Score distributions
- Expected value curves
- Bust probability charts
- Strategy comparison plots

---

### ⚙️ Custom Simulation Settings

Experiment with different game conditions.

Options include:

- Number of players
- Simulation count
- Custom stopping strategies

---

## Technology

- **Python**
- **Matplotlib**
- **Monte Carlo Simulation**
- **Probability Theory**
- **Game Theory**

---

## Project Goals

This project is designed to:

- Apply probability theory to a real game
- Explore Monte Carlo simulation techniques
- Analyze risk versus reward decisions
- Compare human and optimal strategies
- Develop data visualization skills
- Demonstrate statistical decision-making using large simulated datasets


## License

This project is licensed under the MIT License.
