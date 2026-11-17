---
roles: [ai-ml-engineer, data-science]
topics: [gradient descent, optimization, learning rate]
---
# Gradient Descent and Optimization

Gradient descent minimises a loss function by repeatedly stepping parameters in the direction of steepest decrease, the negative gradient. The learning rate controls step size: too large and training diverges or oscillates; too small and it crawls or stalls in flat regions.

Batch gradient descent uses the whole dataset per step (stable but slow). Stochastic gradient descent uses one example per step (noisy but fast and able to escape shallow minima). Mini-batch gradient descent is the practical compromise and the standard for neural networks.

Modern optimizers add memory: momentum accumulates past gradients to push through flat spots; Adam combines momentum with per-parameter adaptive learning rates and is the default starting point for deep learning. Learning-rate schedules (decay, warmup, cosine annealing) usually beat a fixed rate.

Loss choice matters: mean squared error for regression, cross-entropy for classification, and task-specific losses (for example, focal loss for extreme imbalance). The loss must be differentiable with respect to the parameters being learned.
