---
roles: [ai-ml-engineer, data-science]
topics: [overfitting, regularization, bias-variance, generalisation]
---
# Overfitting, Regularization and the Bias-Variance Tradeoff

Overfitting happens when a model learns the noise in the training data as well as the signal, so training error keeps falling while validation error rises. Underfitting is the opposite: the model is too simple and performs poorly even on training data.

The bias-variance tradeoff frames this tension. Bias is error from wrong assumptions in the model (too simple). Variance is error from sensitivity to small changes in the training set (too complex). Total expected error is roughly bias squared plus variance plus irreducible noise. More model capacity reduces bias but raises variance.

Regularization controls capacity. L2 (ridge) penalises large weights, shrinking them toward zero. L1 (lasso) can drive weights exactly to zero, doing feature selection. Dropout randomly disables neurons during training in neural networks. Early stopping halts training when validation error stops improving.

Practical defences: cross-validation to measure generalisation honestly, more or cleaner training data, simpler models, feature selection, and data augmentation where it makes sense for the domain.
