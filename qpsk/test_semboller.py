import numpy as np

np.random.seed(42)
bitler = np.random.randint(0, 2, size=16)
print("Bitler:", bitler)
print("Ciftler:", [(bitler[i], bitler[i+1]) for i in range(0, 16, 2)])
