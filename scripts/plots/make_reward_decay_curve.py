import matplotlib.pyplot as plt
import numpy as np

alpha = np.linspace(0, 0.99, 500)

k_values = [0, 1, 2, 3, 4, 5]

fig, ax = plt.subplots(figsize=(7, 4.5))

for k in k_values:
    r = (1 - alpha) ** (1 / (2 ** k))
    ax.plot(alpha, r, linewidth=1.8, label=f'$k = {k}$')

ax.set_xlabel(r'Chunk saturation ratio $\alpha$', fontsize=12)
ax.set_ylabel(r'Reward ratio $', fontsize=12)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1.05)
ax.legend(fontsize=11, loc='upper right')
ax.grid(True, alpha=0.3)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig('../../src/img/reward-decay-curve.pdf', bbox_inches='tight')
plt.savefig('../../src/img/reward-decay-curve.png', dpi=200, bbox_inches='tight')
print("Done")