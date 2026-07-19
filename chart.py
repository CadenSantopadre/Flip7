import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata

# 1. Load your participant data from the CSV file
# Expected columns: 'Card num', 'Bust prob', 'Hit', 'Stay'
df = pd.read_csv('flip7.csv')

# 2. Group the data to find the average choice at each game state
# This smooths individual choices into a coordinate map of probability
grouped = df.groupby(['Cards Out', 'Bust Prob']).agg({
    'Stay': 'mean'  # Output ranges cleanly from 0.0 (always hit) to 1.0 (always stay)
}).reset_index()

Y_data = grouped['Cards Out'].values
X_data = grouped['Bust Prob'].values
Z_data = grouped['Stay'].values

# 3. Create a smooth grid overlay for the contour visualization
x_grid = np.linspace(X_data.min(), X_data.max(), 500)
y_grid = np.linspace(Y_data.min(), Y_data.max(), 500)
X, Y = np.meshgrid(x_grid, y_grid)

# Interpolate the scattered game data onto the dense grid
Z = griddata((X_data, Y_data), Z_data, (X, Y), method='linear')

# 4. Plot the background decision regions
plt.figure(figsize=(9, 7))

# Levels split the map at 0.5 (where decisions flip from Hit to Stay)
# Colors mapping: Red background for hitting (<0.5), Blue for staying (>=0.5)
plt.contourf(X, Y, Z, levels=[0.0, 0.5, 1.0], colors=['#dc4c64', '#3b71ca'], alpha=0.3)

# 5. Draw the human intuition boundary line where Stay Rate equals exactly 50%
plt.contour(X, Y, Z, levels=[0.5], colors=['black'], linewidths=2.5, linestyles='dashed')

# 6. Scatter plot the actual unique game states encountered by players
plt.scatter(X_data, Y_data, c=Z_data, cmap='bwr_r', edgecolors='black', linewidths=0.5, zorder=3)

# 7. Add professional labels and presentation cleanups
plt.title("Human Stopping Decision Boundary in Flip 7", fontsize=14, pad=15)
plt.ylabel("Current Game State (Card Num / Hand Total)", fontsize=11)
plt.xlabel("Calculated Bust Probability", fontsize=11)
plt.grid(True, linestyle=':', alpha=0.5)

# Add a colorbar to show the transition of the human choice gradient
cbar = plt.colorbar(label='Empirical Stay Rate (Human Intuition Threshold)')
cbar.set_ticks([0, 0.5, 1])
cbar.set_ticklabels(['100% Hit (Red)', '50/50 Threshold', '100% Stay (Blue)'])

plt.show()
