---
roles: [ai-ml-engineer, data-science]
topics: [supervised learning, classification, regression]
---
# Supervised Learning

Supervised learning trains a model on labelled examples: each training input comes with the correct output. The model learns a mapping from inputs to outputs so it can predict outputs for unseen inputs.

Two main tasks: classification predicts a discrete label (spam or not spam, disease present or absent); regression predicts a continuous value (house price, temperature).

The training set is split into train, validation and test portions. The model fits parameters on the training set, hyperparameters are tuned against the validation set, and the test set is used once to estimate how the model generalises to new data. Leaking test data into training or tuning inflates reported performance and hides real weaknesses.

Common algorithms include linear regression, logistic regression, decision trees, random forests, gradient boosting, support vector machines, k-nearest neighbours and neural networks. The choice depends on data size, interpretability needs, feature types and latency constraints.

Key risks: overfitting (memorising training noise), underfitting (model too simple to capture the pattern), and label noise or biased labels that the model faithfully reproduces.
