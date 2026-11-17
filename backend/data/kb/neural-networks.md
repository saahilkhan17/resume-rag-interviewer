---
roles: [ai-ml-engineer, data-science]
topics: [neural networks, backpropagation, activation functions]
---
# Neural Networks Fundamentals

A neural network is a stack of layers of simple units. Each unit computes a weighted sum of its inputs plus a bias, then applies a non-linear activation function such as ReLU, sigmoid or tanh. Without non-linearity, any depth of layers collapses into a single linear map.

Training uses backpropagation: the loss gradient is computed layer by layer from the output backwards using the chain rule, and weights are updated by gradient descent. Weights are initialised carefully (for example, He or Xavier initialisation) because poor initialisation causes vanishing or exploding gradients.

Depth lets networks learn hierarchical features: early layers detect edges or simple patterns, later layers combine them into objects or concepts. This is why deep learning excels on images, audio and text, where raw features are not informative on their own.

Common failure modes: overfitting on small datasets, vanishing gradients in very deep networks (mitigated by residual connections and normalisation layers), and sensitivity to data scaling, so inputs are usually standardised.
