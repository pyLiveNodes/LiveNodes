import matplotlib.pyplot as plt

import numpy as np

import seaborn as sns
sns.set_style("darkgrid")
sns.set_context("paper")
sns.set_palette('deep')


labels = ['Front/Back', 'Left/Right', 'Speed', 'Knee Cycle']
means_1 = np.array([0.05, 0.02, 0.6, 0.7])
means_2 = np.array([0.15, 0.95, 0.3, 0.1])
means_3 = np.array([0.8, 0.03, 0.1, 0.2])
width = 0.35       # the width of the bars: can also be len(x) sequence

fig, ax = plt.subplots()

ax.set_ylim(0, 1)
ax.set_xlim(-0.5, 3.5)

ax.bar(labels, means_1, width, )
ax.bar(labels, means_2, width, bottom=means_1)
ax.bar(labels, means_3, width, bottom=means_1 + means_2)

ax.text(x=-0.2, y=0.02, s="Forward", ha='right', va='bottom', rotation="vertical", color='black', fontsize=12)
ax.text(x=0.8, y=0.02, s="None", ha='right', va='bottom', rotation="vertical", color='black', fontsize=12)
ax.text(x=1.8, y=0.02, s="Low", ha='right', va='bottom', rotation="vertical", color='black', fontsize=12)
ax.text(x=2.8, y=0.02, s="Cyclic", ha='right', va='bottom', rotation="vertical", color='black', fontsize=12)

ax.set_ylabel('Score')
ax.set_xlabel('Features')
ax.set_title('High-Level Features')

# plt.show()
plt.tight_layout()
plt.savefig('mockup.png')