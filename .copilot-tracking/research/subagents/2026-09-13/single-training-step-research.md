---
title: "Module 1: What Actually Happens When a Model Is Trained"
description: "Implementation-deep first lesson with a verified scalar training step and an independent CPU PyTorch lab"
ms.date: 2026-09-13
ms.topic: tutorial
---

Data -> Tokenization -> Dataset -> Model -> Forward Pass -> Loss -> Backprop -> Gradients -> Optimizer -> Weight Update -> Checkpoint -> Evaluation -> Deployment -> Inference -> Monitoring -> Feedback -> Retraining

Tokenization is the NLP-specific representation stage in this journey, not a
requirement for scalar regression. Other modalities have their own representations.
The arrows name dependencies, not a once-through pipeline. Forward through weight
update repeats over batches; validation and checkpointing recur; deployment needs
an approval gate; feedback can start a new, versioned training cycle.

## A - Executive understanding

Training changes numerical parameters so a chosen objective becomes smaller on
training examples. It does not install factual records into a searchable database,
prove that predictions are correct, or authorize deployment. The executable model
defines a family of functions. Data, the objective, initialization, and optimization
determine which member of that family you obtain.

Use one scalar input, one scalar output, and two trainable numbers:
$\hat y=wx+b$. You already know the function's form; training estimates its slope
and intercept. A neural network replaces this function with a composition of many
parameterized operations. The forward/loss/backward/update contract remains.

The first lesson's success criterion is operational: predict every number in one
update, identify which objects mutate, diagnose a wrong gradient, and distinguish
an optimization check from evidence of generalization. Spend one session deriving
the numbers and another running and inspecting the independent lab.

An important correction is part of the lesson. With the specified data and update,
the new loss is **0.59625, not 0.5625**. Exact rational arithmetic verified this;
the requested 0.5625 failed a check. A plausible expected value is not evidence.

Different roles own different parts of the same step:

| Perspective | Responsibility and evidence |
|-------------|-----------------------------|
| Developer | Tensor contracts, graph connectivity, assertions, and executable updates |
| ML engineer | Objective, split validity, normalization, optimization, and evaluation |
| Platform engineer | Data delivery, memory, reproducible runtimes, and recoverable state |
| Architect | Training/serving boundaries, artifact contracts, release gates, and rollback |
| Principal engineer | Whether evidence supports the business decision and the claimed operating envelope |

No learner proficiency is inferred from reading. The knowledge map at the end
separates covered topics from demonstrated competence.

## B - Mental model

Imagine two adjustable knobs, $w$ and $b$. A forward pass asks what the current
knob settings predict. The loss measures a specified discrepancy. Backpropagation
computes local sensitivity: how changing each knob infinitesimally would change
that loss. The optimizer chooses a finite adjustment from those sensitivities,
its hyperparameters, and possibly its history.

A gradient is not the update. It does not contain a learning rate, and it is not
a promise of future improvement. A negative derivative means increasing that
parameter locally decreases the objective while other parameters are fixed.
Subtracting the gradient therefore moves in the locally decreasing direction.
Large moves can leave the region where that local description is useful.

Keep three kinds of state separate:

* Persistent learned state: parameters and relevant model buffers
* Temporary computation state: activations, saved tensors, and the current graph
* Training continuation state: gradient buffers, optimizer history, random-number
  generators, data position, schedules, and progress counters

A batch contains examples processed together. A step usually means one optimizer
update. An epoch means one traversal of the designated training set. Gradient
accumulation allows multiple microbatches per step; streaming datasets may not
have a natural epoch. Always say which counter a graph or checkpoint uses.

In the lab, data is ordinary numeric tensors. In language modeling, text first
becomes token IDs, then embeddings and other representations. Token IDs are
discrete identifiers, not differentiable real-valued inputs; selected embedding
weights receive gradients. Tokenizer construction and transformer internals are
deferred. CNNs reuse filters across spatial positions; RNNs reuse transition
parameters across time. Their shapes and backward details belong in later modules.

## C - Technical mechanics

### Tensor contracts before algorithms

For batch size $B=2$, use inputs and targets of shape `[B, 1]`, not one of shape
`[B]` and the other `[B, 1]`. Broadcasting that mismatch can produce a `[B, B]`
error matrix comparing every prediction with every target. The code may run while
optimizing the wrong objective.

`nn.Linear(1, 1)` stores weight shape `[1, 1]` and bias shape `[1]`. Its operation is
$XW^T+b$, giving output `[B, 1]`; bias broadcasts across rows. The mean squared
error reduces all output elements to a scalar with shape `[]`. With one output
per example, averaging elements is the same as averaging examples. That equivalence
needs reconsideration for multiple outputs, masks, and per-example weights.

### Graph construction and leaf parameters

Assigning an `nn.Parameter` to a module attribute registers it as module state;
the wrapper normally enables `requires_grad`. These parameters are leaves and
have no producing `grad_fn`.
The output and loss are non-leaf results with graph history when computed in grad
mode. Inputs need not require gradients for parameter gradients to be computed.

Eager autograd records the operations actually executed and saves needed values.
A fresh forward creates a fresh graph. `loss.backward()` starts with
$\partial L/\partial L=1$ for a scalar loss and traverses dependencies in reverse,
applying chain rule and summing contributions from shared uses [S1]. Reverse-mode
autodiff is neither finite differences nor symbolic algebra over the whole program.
It applies implemented local derivatives at the current numerical values.

By default, leaf parameters accumulate results into `.grad`. Intermediate gradients
are used during backward but not retained in their `.grad` fields; use
`retain_grad()` on a chosen non-leaf before backward if inspection is necessary.
Saved tensors are normally released during backward. Reusing the same consumed
graph is different from doing a fresh forward; routinely setting `retain_graph=True`
is not the solution to a broken training loop.

### Four APIs with different jobs

| Operation | What changes | What it does not do |
|-----------|--------------|---------------------|
| `optimizer.zero_grad(set_to_none=True)` | Assigned parameter gradient fields become `None` | Does not reset weights or momentum |
| `model(x)` and loss construction | Predictions, scalar loss, and graph | Does not apply an optimizer update |
| `loss.backward()` | Accumulates parameter gradients | Does not change ordinary model weights |
| `optimizer.step()` | Updates assigned parameters and optimizer state | Does not normally clear gradients |

Two fresh forwards and backwards without clearing gradients add two contributions.
That can implement intentional accumulation or an accidental larger update.
Conversely, clearing gradients between backward and step removes the information
the optimizer needs. Clearing once at the start of an intended update is explicit.

`None` and a zero tensor are not equivalent [S3]. Optimizers generally skip a
parameter whose gradient is `None`; a zero gradient can still permit momentum or
weight decay to move it. Check for `None` before inspecting a gradient norm.
The optimizer only knows parameters passed to it, not every tensor in your model.

`model.train()` and `model.eval()` select module behavior, such as dropout and
BatchNorm. They do not enable or disable autodiff. `torch.no_grad()` prevents graph
recording for ordinary operations; it does not select evaluation behavior.
Validation normally needs both `eval()` and a no-grad context. The lone linear
layer has no mode-sensitive behavior, but preserving this contract avoids future
bugs [S1]. Ordinary optimizer updates run without recording a new gradient graph;
differentiable optimization is a separate advanced use case.

## D - Mathematics with a verified step

### Forward and loss

Let $x=[1,2]$, $y=[2,4]$, $w_0=0.5$, $b_0=0$, and learning rate $\eta=0.1$.
Both parameters update together from gradients evaluated at the old state.

$$
L(w,b)=\frac{1}{B}\sum_{i=1}^{B}(wx_i+b-y_i)^2.
$$

| Example | Input | Target | Prediction | Residual | Squared residual |
|---------|-------|--------|------------|----------|------------------|
| 1 | 1 | 2 | 0.5 | -1.5 | 2.25 |
| 2 | 2 | 4 | 1.0 | -3.0 | 9.00 |

Therefore $L_0=(2.25+9)/2=5.625$. There is no extra factor of one-half in this
definition. Textbooks sometimes use one; mixing conventions changes gradients.
Loss has squared target units, so comparing its raw value across differently
scaled targets can mislead.

### Backward through each operation

Define $z_i=wx_i+b$, $e_i=z_i-y_i$, and $q_i=e_i^2$. The local derivatives are
$\partial L/\partial q_i=1/B$, $\partial q_i/\partial e_i=2e_i$,
$\partial e_i/\partial z_i=1$, $\partial z_i/\partial w=x_i$, and
$\partial z_i/\partial b=1$. Multiplying along each path and adding paths gives:

$$
\frac{\partial L}{\partial w}
=\sum_i\frac{1}{B}(2e_i)(1)x_i
=\frac{2}{2}[(-1.5)(1)+(-3)(2)]=-7.5,
$$

$$
\frac{\partial L}{\partial b}
=\sum_i\frac{1}{B}(2e_i)(1)(1)
=\frac{2}{2}[-1.5-3]=-4.5.
$$

The prediction gradient is $[-1.5,-3]$ for this batch. The slope's second-example
contribution is larger because the local derivative of $wx_2$ with respect to
$w$ is $x_2=2$. Summation is required because the same parameters serve both rows.
Autograd handles this sharing; it does not assign a separate weight to each row.

### Update and recompute

Plain SGD without momentum or decay applies $\theta_1=\theta_0-\eta g_0$:

$$
w_1=0.5-0.1(-7.5)=1.25,\qquad
b_1=0-0.1(-4.5)=0.45.
$$

The new predictions are $[1.70,2.95]$, so the new residuals are $[-0.30,-1.05]$:

$$
L_1=\frac{(-0.30)^2+(-1.05)^2}{2}
=\frac{0.09+1.1025}{2}=\frac{477}{800}=0.59625.
$$

That is the corrected value, not 0.5625. The original `loss` tensor still contains
the pre-update value. Recompute a forward to measure the post-update loss. This
is a same-batch optimization diagnostic, not validation or test performance.

A finite-difference cross-check approximates
$\partial L/\partial w$ by
$[L(w+h,b)-L(w-h,b)]/(2h)$. It is useful for tiny diagnostic cases, not a
replacement for reverse-mode autodiff over millions of parameters. Choosing $h$
too small amplifies floating-point cancellation; too large introduces approximation
error for general nonlinear functions.

### Beyond plain SGD

One common momentum convention is $v_t=\mu v_{t-1}+g_t$ and
$\theta_t=\theta_{t-1}-\eta v_t$, with zero initial velocity, no dampening, and
no Nesterov term. Momentum remembers past directions, so resuming with weights
alone generally changes the next update. Library conventions matter [S2].

For ordinary Adam without weight decay or AMSGrad, operations below are elementwise:

$$
m_t=\beta_1m_{t-1}+(1-\beta_1)g_t,\quad
v_t=\beta_2v_{t-1}+(1-\beta_2)g_t^2,
$$

$$
\hat m_t=\frac{m_t}{1-\beta_1^t},\quad
\hat v_t=\frac{v_t}{1-\beta_2^t},\quad
{}\theta_t=\theta_{t-1}-\eta_t\frac{\hat m_t}{\sqrt{\hat v_t}+\epsilon}.
$$

The second moment tracks squared gradients, not the centered statistical variance.
Bias correction compensates for starting the moment estimates at zero. AdamW
decouples decay from those moments:

$$
{}\theta_t=(1-\eta_t\lambda)\theta_{t-1}
-\eta_t\frac{\hat m_t}{\sqrt{\hat v_t}+\epsilon}.
$$

Here $g_t$ is the data-objective gradient. Traditional coupled Adam decay instead
adds $\lambda\theta$ to the gradient before forming moments. These operations are
not generally equivalent under adaptive scaling [S4, S5]. Neither algorithm
guarantees monotonic loss on consecutive stochastic batches.

For a finite objective $N^{-1}\sum_i\ell_i(\theta)$, uniformly sampled examples
give an unbiased mean gradient at a fixed $\theta$. This assumes the sampling
and reduction match the objective. Unequal sampling without correction changes
the expectation. Random reshuffling is not conditionally identical to independent
sampling at every evolving parameter state. Batch-dependent operations, clipping,
variable-length normalization, and data-dependent filtering require separate
analysis. An unbiased gradient is not an unbiased Adam update or proof of
generalization to production.

## E - Implementation decisions

Construct the model on its intended device and dtype before constructing the
optimizer. Parameter identity matters: replacing a parameter object afterward can
leave the optimizer attached to an obsolete object. For initialization, use
`torch.no_grad()` and in-place `fill_`, not `.data` mutations that bypass useful
autograd safety checks. Fixed initial values isolate arithmetic from randomness.

Use floating targets for regression. Check input/output/target shape equality,
finite loss, nonmissing gradients for expected parameters, finite gradient values,
and actual parameter movement. Logging a changing loss alone cannot identify a
wrong target, broken graph, or missing optimizer parameter.

The lab first uses double precision to make arithmetic inspection convenient,
then trains another linear model on different points. It does not import ARISE-X,
download datasets, need GPUs, or depend on notebook state. Preprocessing is fitted
on training values only. Validation selects a snapshot; test is scored once after
that selection. Copy selected state rather than keeping a live `state_dict`
reference [S8].

For standardized input $z=(x-\mu)/\sigma$, the learned function is $az+c$.
Its raw-space slope and intercept are $a/\sigma$ and $c-a\mu/\sigma$.
Comparing standardized $a$ directly with the raw target slope 2 is a diagnostic
mistake. Persist the transform, its feature ordering, and the expected dtype with
the weights. Serving must reuse, not refit, it.

## F - Infrastructure and scale preview

### Memory is not weight size

For $P$ parameters in all-FP32 Adam, a common planning baseline is 4 bytes for
weights, 4 for gradients, and 8 for two moments: $16P$ bytes. At one billion
parameters that is 16 GB decimal, about 14.9 GiB, before activations or overhead.
This is an assumption, not a universal training-memory formula.

Activation memory depends on batch size, depth, representation size, sequence
length, and which intermediates backward saves. Add temporary kernels, allocator
reservation, communication buckets, buffers, and checkpoint staging. Optimizer
state may be allocated on the first update, explaining failures after a successful
forward. FP64 doubles the four-array baseline; plain SGD has fewer arrays.
Mixed-precision master weights, low-bit optimizers, and state sharding alter the
accounting. Measure peak allocated and reserved memory on the actual workload.

CPU data decoding, local RAM, storage bandwidth, and host-to-device transfer can
starve accelerators. Profile data wait, forward, backward, optimizer, and checkpoint
time separately. A GPU utilization percentage alone does not locate the bottleneck.
For two scalar parameters, CPU is the appropriate infrastructure.

### Accumulation with the correct denominator

For $K$ equally sized microbatches and an additive mean objective, divide each
microbatch mean by $K$, backward each, and step once. With different valid token
counts $n_k$, averaging their means equally is wrong for a token-mean objective:

$$
L=\frac{\sum_k\sum_{j=1}^{n_k}\ell_{kj}}{\sum_k n_k}
=\sum_k\frac{n_k}{N_{\mathrm{valid}}}L_k.
$$

If one microbatch has 2 valid tokens and another has 8, the weights are 0.2 and
0.8, not 0.5 each. Mask padding, count the objective's valid elements, and reject
an all-masked window. Backward each summed loss divided by the window's total
count, or accumulate summed gradients and divide once before clipping and stepping.
Do not step between microbatches. Handle the final partial window explicitly.
For weighted losses, use the objective's actual weight denominator.

Equivalence to one large batch also assumes unchanged parameters and compatible
per-example computations. BatchNorm, dropout sampling, rounding, or clipping each
microbatch separately can break exact equivalence.

### Precision and placement

FP16 has limited exponent range; gradients can underflow, and values can overflow
to infinity. Autocast selects precision per operation. A gradient scaler multiplies
the loss, then unscales gradients before inspection or clipping. Nonfinite gradients
can cause the optimizer update to be skipped and the scale adjusted. Keep the
scale unchanged across an accumulation window; unscale once after accumulation,
then clip, step, and update the scaler [S6]. Track successful updates separately
from attempted batches and keep scheduler timing consistent with the chosen policy.

BF16 has FP32-like exponent range but fewer significand bits; it often avoids the
need for FP16-style scaling. It is not immune to rounding, instability, or NaNs.
Hardware support and operation policies matter. Neither precision mode is exercised
by this CPU FP64 lab.

Data parallelism replicates parameters, usually with one process per GPU; each
replica computes local gradients and communication combines them before the update.
Equal local means can be averaged for equal counts. With unequal token counts,
default averaging over $R$ ranks requires appropriate global normalization; for
summed local losses, scaling by $R/N_{\mathrm{global}}$ before the averaged reduction
produces the global token-mean gradient. Custom communication semantics can differ.
State sharding partitions optimizer/gradient/parameter storage; tensor and pipeline
parallelism partition computation. These are placement previews, not distributed
implementation exercises or later-module design solutions.

## G - Production architecture

Separate the reproducible training job from the request-serving process. Training
consumes a versioned dataset and configuration, emits checkpoints and evaluation
evidence, and proposes a candidate artifact. Serving loads an approved inference
artifact and preprocessing contract, validates requests, and produces predictions.
Serving normally needs neither labels, backward graphs, nor optimizer moments.

```text
Versioned data + split manifest + configuration
	-> train-only preprocessing fit -> training worker -> recovery checkpoint
	-> validation selection -> frozen candidate -> independent test evidence
	-> approval / registry -> staged serving rollout -> monitored predictions
	-> reviewed outcomes and labels -> new data version -> retraining proposal
```

A recovery checkpoint needs more than deployable weights: model and optimizer
state, step/epoch and data cursor, random states, configuration, preprocessing and
schema, dataset identity, code revision, and runtime versions. Add scheduler and
AMP scaler state when used. Multiworker loading, CUDA RNGs, and partial accumulation
need their own continuation state. A seed restarts a sequence; an RNG state resumes
its current position.

Write durable checkpoints with integrity checks and atomic publication. Test actual
restoration rather than inferring recovery from a successful write. The lab uses
an in-memory serialization round trip to demonstrate the state contract; it does
not claim durability, process-crash recovery, or cross-machine bitwise replay.
Only load trusted artifacts; `weights_only=True` narrows the deserialization surface
but does not make arbitrary files harmless [S8].

Release evidence includes useful task performance, relevant slices, latency,
resource cost, schema compatibility, and rollback readiness. Monitoring covers
input validity, feature distributions, operational health, and outcomes when labels
arrive. Drift is an investigation signal, not automatic proof that retraining will
help. Feedback can be delayed, selected by the current model, incorrectly labeled,
or unsuitable for retention. Version, review, and deduplicate it before proposing
new training data. Deployment and retraining are controlled loops, not automatic
consequences of a falling training loss.

## H - Failure modes

| Failure | Mechanism | Prevention or evidence |
|---------|-----------|------------------------|
| Wrong broadcasting | `[B]` targets meet `[B,1]` predictions | Assert equal shapes before loss |
| Missing gradients | Detach, conversion to a Python number, or no-grad forward | Inspect `requires_grad`, `grad_fn`, and leaf `.grad` |
| Stale gradient accumulation | Clear omitted across intended steps | Track update boundaries and inspect gradients |
| No parameter movement | Wrong optimizer parameters or clearing after backward | Compare identity and before/after tensors |
| Exploding loss | Excessive step size, invalid data, or bad scaling | Check finite values and gradient/update norms |
| Misleading validation | Scoring the training batch or fitting transforms on all data | Version disjoint splits and train-only fitting |
| Resume divergence | Optimizer, RNG, cursor, or preprocessing omitted | Compare the next batch and next update |
| Gradual memory growth | Retained graphs or stored graph-connected outputs | Store detached metrics and inspect references |
| Production mismatch | Different feature units, order, or preprocessing | Enforce versioned serving contracts |

A zero gradient can be mathematically correct; `None` can be expected for an unused
branch. Diagnose against the intended graph rather than treating all missing or
small values as bugs. Decreasing loss can coexist with data leakage or learning an
undesired proxy. Numerical health is necessary but not sufficient.

## I - Troubleshooting workflow

Start with the smallest fixed batch and fixed weights. Record shapes, dtype,
device, predictions, target alignment, reduction, and finite-value checks before
changing the optimizer. Reproduce the hand-computed step; if it fails, increasing
the model size only makes diagnosis harder.

Next inspect leaf gradients immediately after backward and parameters immediately
after step. Log gradient norm and update norm separately. If gradients exist but
weights do not move, examine learning rate, optimizer membership, and precision.
If a loss has no graph, find the first detached conversion rather than adding
`requires_grad=True` to the final scalar, which cannot reconnect earlier operations.

For NaNs, identify the first nonfinite tensor. Invalid operations can poison
backward even if their outputs are masked later; prevent the invalid operation
before recording it [S1]. Temporarily use anomaly detection for a small reproduction,
not as an always-on performance setting. Compare with higher precision when useful.

For a resume mismatch, compare artifacts in causal order: configuration and data
IDs, transform statistics, next batch, pre-step parameters, forward output, gradient,
optimizer buffers, then post-step weights. Same weights with different moments are
not the same training state. A deterministic test should isolate the divergence
before investigating hardware nondeterminism.

Finally separate optimization from generalization. A model that cannot fit a small
clean subset suggests an implementation or capacity problem. A model that fits
training but fails held-out data suggests split, distribution, capacity, or selection
issues. Do not repeatedly tune against test outcomes; that turns the test set into
another development set.

## J - Tradeoffs and decision boundaries

| Choice | Benefit | Cost or boundary |
|--------|---------|------------------|
| Tiny CPU FP64 example | Inspectable arithmetic and no accelerator dependency | Not representative throughput or memory |
| Larger batch | Efficient parallel work and less sampling noise in many settings | More activation memory and different optimization behavior |
| Accumulation | Larger effective batch without storing all activations together | More latency and normalization/mode subtleties |
| Momentum or AdamW | History-aware updates or coordinate adaptation | Extra state, memory, and recovery obligations |
| More frequent checkpoints | Less lost work on failure | Storage bandwidth, cost, and checkpoint consistency work |
| Deterministic execution | Easier diagnosis and regression comparison | Potential slowdown; no cross-platform guarantee |
| Repeated validation | Informs selection and stopping | Can overfit development decisions to validation |

Choose the simplest setup that can falsify your current hypothesis. The first
hypothesis is that the step implementation matches its mathematics. Distributed
training, larger models, and elaborate dashboards cannot compensate for a failure
at that boundary. Later decisions should optimize quality and cost together, not
maximize hardware complexity.

## K - Difficult interview question and assessment bank

The difficult interview question is P1 below. It is counted once within the exact
28-prompt bank. No answers are supplied. Explain assumptions and what evidence
would distinguish competing explanations when practicing.

### Beginner prompts - 5

1. B1: What is learned in $\hat y=wx+b$, and what remains fixed during one step?
2. B2: How do a batch, a step, and an epoch differ?
3. B3: What does a negative parameter gradient mean locally?
4. B4: Why is the loss usually reduced to a scalar before calling backward?
5. B5: Why is lower training loss not proof of better production predictions?

### Intermediate prompts - 5

1. I1: Trace the shapes through `nn.Linear(1,1)` and mean squared error.
2. I2: What happens after two fresh backwards without clearing gradients?
3. I3: How do `eval()` and `no_grad()` differ, and when are both needed?
4. I4: What distinguishes a leaf parameter from a non-leaf prediction tensor?
5. I5: Why must input normalization be fitted on training data only?

### Senior prompts - 5

1. S1: When can a zero gradient lead to a different update from `None`?
2. S2: Which assumptions make a sampled mean gradient unbiased?
3. S3: How would you normalize accumulation across unequal valid-token counts?
4. S4: Why does restoring only weights change momentum or Adam continuation?
5. S5: How would you determine whether a memory failure comes from activations or optimizer state?

### Principal prompts - 5

1. P1: A resumed job has identical weights and next-batch loss but takes a different next update; what evidence is needed to establish the cause and decide whether the run remains comparable?
2. P2: Which guarantees would you require before calling a training artifact reproducible?
3. P3: How would you distinguish an implementation regression from a distribution shift?
4. P4: When should improved offline metrics still fail a deployment gate?
5. P5: What assumptions would you challenge in a 16-bytes-per-parameter capacity estimate?

### Design prompts - 3

1. D1: Design a versioned contract connecting training preprocessing and inference.
2. D2: Design a minimal CPU experiment that separates optimization correctness from generalization evidence.
3. D3: Design a checkpoint boundary that makes recovery testable without storing a computation graph.

### Troubleshooting prompts - 3

1. T1: Predictions are `[32,1]` and targets are `[32]`; how would you investigate unexpectedly smooth training?
2. T2: Parameters stop changing after a refactor although gradients remain nonzero; what would you inspect?
3. T3: A mixed-precision run skips many updates; how would you isolate numerical and data causes?

### Whiteboard prompts - 2

1. W1: Derive both gradients and one SGD update for an arbitrary two-example scalar regression batch.
2. W2: Derive the correctly weighted mean loss for two microbatches with different numbers of valid targets.

## L - Independent CPU PyTorch lab

### 1 Objective

Verify the specified single step, distinguish backward from update and clearing,
train with separate partitions, and compare an uninterrupted next update against
a restored one. The lab is intended to run independently; its PyTorch runtime
has **not** been executed in this research session.

### 2 Architecture

A Python process owns CPU models with one `nn.Linear` layer each,
numeric tensors, an SGD optimizer, and an in-memory checkpoint. The arithmetic
probe uses SGD without momentum. The separate training exercise uses momentum
0.9 so checkpoint recovery must restore nonempty optimizer state. Six training
points, three validation points, and three test points have disjoint input values.
All follow the intentionally trivial relation $y=2x$.

### 3 Prerequisites

Use Python 3.11+ supported by your chosen PyTorch wheel, basic Python functions,
and the arithmetic above. No CUDA, account, external dataset, or application
dependency is required. The following PowerShell commands are instructions for
a future learner, not commands executed during research. From the workspace root,
create a separate lab environment under research; do not use the app's `.venv`.

```powershell
$lab = Join-Path $PWD '.copilot-tracking/research/labs/module-1'
New-Item -ItemType Directory -Force -Path $lab | Out-Null
$env:UV_CACHE_DIR = Join-Path $lab 'uv-cache'
uv venv (Join-Path $lab '.venv') --python 3.11
$python = Join-Path $lab '.venv/Scripts/python.exe'
uv pip install --python $python torch --index-url https://download.pytorch.org/whl/cpu
uv pip install --python $python ipykernel ipywidgets ruff tqdm pytest
```

Choose a CPU wheel compatible with your operating system using the official
PyTorch installer if needed [S9]. The extra tools follow local environment
conventions, not runtime requirements of this script. Pin the tested versions
when turning the exercise into a reproducible course distribution. Save the
following code as .copilot-tracking/research/labs/module-1/train_step.py, then run:

```powershell
& $python -B (Join-Path $lab 'train_step.py')
```

### 4 Code

```python
#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# SPDX-License-Identifier: MIT
"""Inspect a scalar training step and a CPU checkpoint round trip.

Run with Python -B in a separate PyTorch environment. Writes no files.
"""

from __future__ import annotations

import copy
import io
import logging
import random
import sys
from typing import Any

import torch
from torch import nn

LOGGER = logging.getLogger(__name__)
DTYPE = torch.float64


def make_model() -> nn.Linear:
	"""Create CPU leaf parameters with fixed initial values."""
	model = nn.Linear(1, 1, dtype=DTYPE, device="cpu")
	with torch.no_grad():
		model.weight.fill_(0.5)
		model.bias.fill_(0.0)
	return model


def objective(model: nn.Linear, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
	"""Compute scalar MSE after validating the tensor contract."""
	prediction = model(x)
	if prediction.shape != y.shape or x.ndim != 2 or x.shape[1] != 1:
		raise ValueError("Expected inputs, predictions, targets with shape [B, 1]")
	loss = (prediction - y).square().mean()
	if not bool(torch.isfinite(loss)):
		raise FloatingPointError("Loss is nonfinite; inspect data and predictions")
	return loss


def score(model: nn.Linear, x: torch.Tensor, y: torch.Tensor) -> float:
	"""Evaluate without building a graph; caller restores training mode."""
	model.eval()
	with torch.no_grad():
		return objective(model, x, y).item()


def update(
	model: nn.Linear, optimizer: torch.optim.Optimizer,
	x: torch.Tensor, y: torch.Tensor,
) -> float:
	"""Apply one update and return the pre-update loss."""
	model.train()
	optimizer.zero_grad(set_to_none=True)
	loss = objective(model, x, y)
	loss.backward()
	for parameter in model.parameters():
		if parameter.grad is None or not bool(torch.isfinite(parameter.grad).all()):
			raise FloatingPointError("Expected a finite gradient for each parameter")
	optimizer.step()
	return loss.item()


def verify_single_step() -> None:
	"""Assert forward, backward, mutation, and clearing independently."""
	x = torch.tensor([[1.0], [2.0]], dtype=DTYPE)
	y = torch.tensor([[2.0], [4.0]], dtype=DTYPE)
	model = make_model()
	optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
	optimizer.zero_grad(set_to_none=True)
	assert model.weight.is_leaf and model.weight.grad_fn is None
	torch.testing.assert_close(model(x), torch.tensor([[0.5], [1.0]], dtype=DTYPE))
	loss = objective(model, x, y)
	assert loss.grad_fn is not None and loss.ndim == 0
	torch.testing.assert_close(loss, torch.tensor(5.625, dtype=DTYPE))
	loss.backward()
	assert model.weight.grad is not None and model.bias.grad is not None
	torch.testing.assert_close(model.weight.grad, torch.tensor([[-7.5]], dtype=DTYPE))
	torch.testing.assert_close(model.bias.grad, torch.tensor([-4.5], dtype=DTYPE))
	assert model.weight.item() == 0.5 and model.bias.item() == 0.0
	old_gradient = model.weight.grad.clone()
	optimizer.step()
	torch.testing.assert_close(model.weight, torch.tensor([[1.25]], dtype=DTYPE))
	torch.testing.assert_close(model.bias, torch.tensor([0.45], dtype=DTYPE))
	torch.testing.assert_close(model.weight.grad, old_gradient)
	after = score(model, x, y)
	torch.testing.assert_close(torch.tensor(after, dtype=DTYPE),
							   torch.tensor(0.59625, dtype=DTYPE))
	LOGGER.info("step loss=%.6f dw=-7.500000 db=-4.500000", loss.item())
	LOGGER.info("new w=%.6f b=%.6f same_batch_mse=%.6f",
				model.weight.item(), model.bias.item(), after)
	optimizer.zero_grad(set_to_none=True)
	assert all(p.grad is None for p in model.parameters())
	# Fresh graphs, unchanged weights: demonstrate accumulation deliberately.
	objective(model, x, y).backward()
	first = model.weight.grad.clone()
	objective(model, x, y).backward()
	torch.testing.assert_close(model.weight.grad, 2 * first)
	optimizer.zero_grad(set_to_none=True)


def make_data() -> tuple[dict[str, tuple[torch.Tensor, torch.Tensor]], dict[str, Any]]:
	"""Fit preprocessing only on fixed training records.

	Returns:
		Split tensors and serializable preprocessing metadata.
	"""
	raw = {
		"train": torch.tensor([[-3.0], [-2.0], [-1.0], [1.0], [2.0], [3.0]], dtype=DTYPE),
		"validation": torch.tensor([[-2.5], [0.5], [2.5]], dtype=DTYPE),
		"test": torch.tensor([[-1.5], [0.0], [1.5]], dtype=DTYPE),
	}
	groups = [set(values.flatten().tolist()) for values in raw.values()]
	assert all(groups[i].isdisjoint(groups[j])
			   for i in range(3) for j in range(i + 1, 3))
	mean = raw["train"].mean().item()
	scale = raw["train"].std(correction=0).item()
	if scale <= 0:
		raise ValueError("Training feature must have positive scale")
	preprocessing = {"kind": "standardize", "mean": mean, "scale": scale,
					 "fit_split": "train", "feature_order": ["x"]}
	splits = {name: ((values - mean) / scale, 2 * values)
			  for name, values in raw.items()}
	return splits, preprocessing


def snapshot(
	model: nn.Linear, optimizer: torch.optim.Optimizer,
	preprocessing: dict[str, Any], config: dict[str, Any],
) -> bytes:
	"""Serialize a trusted epoch-boundary checkpoint to memory.

	Any is confined to metadata and the library serialization boundary.
	"""
	payload = {
		"schema_version": 1, "architecture": "Linear(1,1)",
		"model": model.state_dict(), "optimizer": optimizer.state_dict(),
		"torch_rng": torch.get_rng_state(), "python_rng": random.getstate(),
		"config": config, "preprocessing": preprocessing,
		"input_schema": {"features": ["x"], "shape": [None, 1], "dtype": "float64"},
		"progress": {"epoch_completed": 1, "step": 3, "next_batch_cursor": 0},
		"dataset": "fixed-disjoint-scalar-v1", "code_revision": "module-1-v1",
		"runtime": {"torch": str(torch.__version__), "python": sys.version},
		"scheduler": None, "scaler": None,
	}
	with io.BytesIO() as buffer:
		torch.save(payload, buffer)
		return buffer.getvalue()


def restore(blob: bytes) -> tuple[nn.Linear, torch.optim.SGD, dict[str, Any]]:
	"""Restore only this exercise's trusted, compatible checkpoint."""
	with io.BytesIO(blob) as buffer:
		payload = torch.load(buffer, map_location="cpu", weights_only=True)
	if payload["schema_version"] != 1 or payload["architecture"] != "Linear(1,1)":
		raise ValueError("Unsupported checkpoint schema or architecture")
	config = payload["config"]
	model = make_model()
	optimizer = torch.optim.SGD(model.parameters(), lr=config["lr"],
								momentum=config["momentum"])
	model.load_state_dict(payload["model"])
	optimizer.load_state_dict(payload["optimizer"])
	# Restore RNG after construction, which itself consumes random numbers.
	torch.set_rng_state(payload["torch_rng"])
	random.setstate(payload["python_rng"])
	model.train()
	return model, optimizer, payload


def verify_resume(
	model: nn.Linear, optimizer: torch.optim.SGD, blob: bytes,
	x: torch.Tensor, y: torch.Tensor,
) -> None:
	"""Compare uninterrupted and restored next updates, including momentum."""
	ids_a = torch.randperm(len(x))[:2]
	loss_a = update(model, optimizer, x[ids_a], y[ids_a])
	state_a = torch.get_rng_state().clone()
	resumed, resumed_optimizer, _ = restore(blob)
	ids_b = torch.randperm(len(x))[:2]
	loss_b = update(resumed, resumed_optimizer, x[ids_b], y[ids_b])
	assert torch.equal(ids_a, ids_b) and loss_a == loss_b
	assert torch.equal(state_a, torch.get_rng_state())
	for original, recovered in zip(model.parameters(), resumed.parameters(), strict=True):
		torch.testing.assert_close(original, recovered, rtol=0, atol=0)
		torch.testing.assert_close(
			optimizer.state[original]["momentum_buffer"],
			resumed_optimizer.state[recovered]["momentum_buffer"], rtol=0, atol=0,
		)
	LOGGER.info("next-step equivalence: PASS (batch, loss, weights, momentum, torch RNG)")


def run_training() -> None:
	"""Train, select by validation, and access test only after selection."""
	config = {"seed": 7, "lr": 0.05, "momentum": 0.9,
			  "batch_size": 2, "epochs": 80, "dtype": "float64", "device": "cpu"}
	random.seed(config["seed"])
	torch.manual_seed(config["seed"])
	torch.set_num_threads(1)
	torch.use_deterministic_algorithms(True)
	splits, preprocessing = make_data()
	train_x, train_y = splits["train"]
	model = make_model()
	optimizer = torch.optim.SGD(model.parameters(), lr=config["lr"],
								momentum=config["momentum"])
	best_value = float("inf")
	best_state = copy.deepcopy(model.state_dict())
	step = 0
	for epoch in range(config["epochs"]):
		order = torch.randperm(len(train_x))
		for ids in order.split(config["batch_size"]):
			update(model, optimizer, train_x[ids], train_y[ids])
			step += 1
		if epoch == 0:
			assert step == 3
			blob = snapshot(model, optimizer, preprocessing, config)
			verify_resume(model, optimizer, blob, train_x, train_y)
			# Discard probe updates; resume from the same clean epoch boundary.
			model, optimizer, restored = restore(blob)
			assert restored["preprocessing"] == preprocessing
			assert restored["progress"]["step"] == step
		validation = score(model, *splits["validation"])
		if validation < best_value:
			best_value = validation
			best_state = copy.deepcopy(model.state_dict())
	model.load_state_dict(best_state)
	test_value = score(model, *splits["test"])
	raw_slope = model.weight.item() / preprocessing["scale"]
	raw_intercept = model.bias.item() - raw_slope * preprocessing["mean"]
	LOGGER.info("steps=%d best_validation_mse=%.8g held_out_test_mse=%.8g",
				step, best_value, test_value)
	LOGGER.info("raw-space slope=%.8g intercept=%.8g", raw_slope, raw_intercept)


def main() -> int:
	"""Run demonstrations and report failures without hidden side effects."""
	logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
	try:
		verify_single_step()
		run_training()
	except KeyboardInterrupt:
		return 130
	except (AssertionError, ValueError, RuntimeError, FloatingPointError):
		LOGGER.exception("Lab failed; compare the first failing contract with the lesson")
		return 1
	return 0


if __name__ == "__main__":
	sys.exit(main())
```

### 5 Explanation

`verify_single_step` checks the pre-update graph and numbers, unchanged weights
after backward, changed weights after step, preserved gradients after step, and
fresh-graph accumulation. Assertions are teaching checks; do not run with `-O`.
`make_data` protects split disjointness and fits normalization once. The synthetic
partitions are genuinely unused for gradient fitting, but their size and known
noise-free relation do not establish performance on a real population.

`snapshot` serializes at the first epoch boundary, after three updates and before
the next shuffle. Thus there is no partial permutation or accumulation to save.
`verify_resume` advances the original branch, reconstructs another model and
optimizer, restores RNG after construction, and compares the next update exactly.
The caller reloads the boundary checkpoint so probe updates do not alter training.
Only the torch RNG drives sampling here; Python RNG is saved as a precaution.
There are no NumPy RNGs, worker processes, GPU states, schedulers, or scalers.

Validation chooses a deep-copied inference snapshot. The selected weights must
not be paired with the final optimizer and called a recovery checkpoint: their
states may come from different steps. The lab's recovery snapshot and best-model
selection deliberately serve different purposes.

### 6 Expected output

These first lines are derived expectations, not a captured PyTorch transcript:

```text
INFO: step loss=5.625000 dw=-7.500000 db=-4.500000
INFO: new w=1.250000 b=0.450000 same_batch_mse=0.596250
INFO: next-step equivalence: PASS (batch, loss, weights, momentum, torch RNG)
```

Final logging should report 240 training updates, finite validation/test MSE, and
raw-space coefficients approaching slope 2 and intercept 0. Exact final metrics
are not asserted or fabricated. Different supported builds may change numerical
details. Seeds and deterministic settings do not guarantee identical results
across releases, devices, or platforms [S7]. The exact replay assertion is scoped
to the same CPU process and compatible runtime.

### 7 Observation

Pause after each single-step operation and inspect values rather than only the
final log. Predict whether `.grad` is `None`, a tensor matching its parameter's
shape, or an accumulated value. Check that validation has no graph and never enters
`update`. Observe that the optimizer's state becomes nonempty with momentum.
Explain why restoring RNG before constructing the replacement model would fail
the batch-order comparison.

### 8 Failures to explore

In a disposable learner copy, remove gradient clearing, reshape a target to `[B]`,
or omit optimizer restoration, one change at a time. State the expected failing
contract before running. Restore the baseline after each experiment. Do not infer
that a passing same-batch check verifies validation independence or production
readiness. An import failure requires the separate environment's dependency setup,
not modification of the application's environment.

### 9 Production equivalent

Replace fixed tensors with a versioned data reader and immutable split manifest;
replace memory serialization with atomic, integrity-checked durable storage;
record exact dependencies and data/code identities; add evaluation slices and
release criteria. Extend continuation state only for features actually used.
Measure a restart in a new process before claiming crash recovery. These are
mapping exercises for this lesson, not solved later-module architectures.

## Five-question quiz - no answers

1. Q1: Which exact state changes during backward, and which changes during step?
2. Q2: Why must both parameter gradients be computed before either parameter is updated in this example?
3. Q3: What new predictions justify the corrected post-update MSE?
4. Q4: Which dataset is allowed to fit preprocessing, select a snapshot, and supply final test evidence?
5. Q5: What additional state beyond weights is needed for the lab's next-step equivalence check?

## Glossary - 10 terms

| Term | Meaning in this lesson |
|------|------------------------|
| Parameter | A learned tensor, such as slope or bias |
| Tensor | A typed multidimensional array with shape and device |
| Mini-batch | A subset processed together to estimate an objective or gradient |
| Forward pass | Evaluation of the parameterized function on inputs |
| Loss | The numerical objective being minimized |
| Computation graph | Recorded operation dependencies needed for differentiation |
| Backpropagation | Reverse application of the chain rule through those dependencies |
| Gradient | Local derivatives of the loss with respect to parameters |
| Optimizer | A rule and optional state that convert gradients into updates |
| Checkpoint | A serialized snapshot sufficient for a stated restoration purpose |

## Knowledge map and evidence of learning

| Capability | Covered here | Earned evidence | Current learner status |
|------------|--------------|-----------------|------------------------|
| Explain the full lifecycle | Journey and production boundaries | Identify repeated loops and approval gates | Not assessed |
| Derive one step | Scalar arithmetic and chain rule | Reproduce numbers without the answer visible | Not assessed |
| Implement a correct update | Tensor and mutation contracts | Run lab and explain each assertion | Not assessed |
| Separate data uses | Train-only transform and held-out partitions | Explain leakage controls and limitations | Not assessed |
| Resume training state | Momentum/RNG serialization | Demonstrate same next batch and update | Not assessed |
| Estimate training resources | State, activation, and overhead accounting | Defend assumptions, then measure | Not assessed |

Reading provides exposure, not earned mastery. CNN/RNN internals, transformer
training, distributed implementations, real-world evaluation design, and production
deployment are not assessed or solved in this module.

## Research evidence and validation status

Status: Complete for bounded research and chapter drafting; PyTorch execution
remains intentionally unperformed. Research questions about step mechanics,
state, data separation, scale boundaries, and teachable implementation are answered
above. No application source, configuration, dependencies, or artifacts were changed.

The bootstrap .copilot-tracking/research/subagents/2026-09-13/learning-plan-preparation-research.md
provided the environment and instruction inventory. Pertinent Markdown, writing,
Python scripting/testing, uv, Python foundational, and Python fact-grounded guidance
were read. Repository memory was consulted. The selected existing venv was configured
and resolved to Python 3.11.15 without installing packages.

Standard-library `fractions.Fraction` verification, executed with `-B`, confirmed
predictions `[0.5, 1.0]`, loss 5.625, gradients -7.5 and -4.5, updated parameters
1.25 and 0.45, predictions `[1.7, 2.95]`, and loss 477/800 = 0.59625. The first
assertion using the supplied 0.5625 failed; corrected exact assertions passed.
The check wrote no files and did not import PyTorch. A recurring error to avoid
is accepting a supplied expected value without recomputing both updated parameters.

Embedded Python passed standard-library AST parsing without imports or execution.
Structural checks confirmed all A-L sections, 28 interview prompts in the requested
5/5/5/5/3/3/2 distribution, five quiz questions, and nine lab fields. The chapter
contains approximately 5,500 words excluding fenced code, plus the 253-line lab.
The editor reported no diagnostics. An attempted formatting-only rewrite truncated
the closing code fence and following sections; they were restored explicitly.
Final checks must use saved-file contents, not assume an editor rewrite is lossless.
The final saved-file check passed Python AST parsing, A-L coverage, assessment
counts, all nine lab fields, corrected mathematical escapes, and complete closing
sections. The editor-backed writer retained indentation tabs and omitted the final
newline; whitespace normalization remains a publication-formatting task, not a
Python syntax failure. No application editor settings were changed to override it.

Numerical derivation is verified independently; API behavior is documentation-grounded;
the full PyTorch lab, checkpoint replay, final convergence, and installation commands
are not runtime-verified. No Pylance runtime/type claim is made for an uninstalled
dependency embedded in Markdown.

### Free sources and supporting claims

Sources were retrieved during this research on 2026-09-13. Stable PyTorch URLs
returned redirect stubs; the linked version-2.14 pages were then retrieved.
This records the documentation served, not a claim that PyTorch 2.14 is installed
or a tested version recommendation. The lab is original explanatory code, not a
copy of course material.

* S1: [PyTorch autograd mechanics](https://docs.pytorch.org/docs/2.14/notes/autograd.html).
	Graph construction, saved tensors, leaf accumulation, grad modes, and mode separation.
* S2: [PyTorch optimizer documentation](https://docs.pytorch.org/docs/2.14/optim.html).
	Parameter ownership, optimizer state, step ordering, and algorithm choices.
* S3: [Optimizer zero_grad](https://docs.pytorch.org/docs/2.14/generated/torch.optim.Optimizer.zero_grad.html).
	`set_to_none` semantics and the distinction between missing and zero gradients.
* S4: [Adam reference](https://docs.pytorch.org/docs/2.14/generated/torch.optim.Adam.html).
	Moment updates, bias correction, coupled decay, and optimizer-state contracts.
* S5: [AdamW reference](https://docs.pytorch.org/docs/2.14/generated/torch.optim.AdamW.html).
	Decoupled weight decay and state/memory considerations.
* S6: [Automatic mixed precision examples](https://docs.pytorch.org/docs/2.14/notes/amp_examples.html).
	Scaling, nonfinite-gradient update skipping, unscaling, clipping, and accumulation.
* S7: [PyTorch reproducibility](https://docs.pytorch.org/docs/2.14/notes/randomness.html).
	Random seeds, deterministic operations, worker RNGs, and portability limits.
* S8: [Saving and loading models](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html).
	State dictionaries, optimizer recovery, copied best-model state, and loading modes.
* S9: [Official PyTorch installation selector](https://pytorch.org/get-started/locally/).
	Learner follow-up for compatible CPU installation; selector not exercised here.
* S10: [Karpathy's official Zero to Hero syllabus](https://karpathy.ai/zero-to-hero.html).
	Confirms the free micrograd introduction and its Python/basic-calculus prerequisites.
	Start with [the backpropagation and micrograd lesson](https://youtu.be/VMj-3S1tku0),
	then derive this chapter's numbers independently. The video was not watched in
	this session, and later course cases are not reproduced or solved here.

### Recommended next research not completed

* [ ] Execute the lab in a separately approved CPU PyTorch environment and record versions.
* [ ] Validate checkpoint continuation across a new process and durable storage.
* [ ] Review installation compatibility for the learner's laptop and pin tested dependencies.
* [ ] Normalize Markdown indentation and the final newline with a verified formatting path.
* [ ] Validate equation/code layout if a parent workflow exports this chapter to PDF.

No clarifying question blocks this chapter. A future teaching session can ask for
the learner's Python/calculus background and laptop constraints before setting pace.