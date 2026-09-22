---
title: Enterprise ML and LLM lifecycle curriculum architecture
description: Stage-gated learning roadmap for an experienced enterprise and Kubernetes architect
ms.date: 2026-09-13
ms.topic: reference
---

## Research scope and status

Status: Complete. Research-only output; no source or environment changes.

Validation confirmed 28 modules, ten levels, ten lab specifications, 486 core
hours, and 118-132 words in each substantive module explanation. All labs remain
unexecuted. The handbook exceeds the suggested word-count range to preserve the
requested per-module contracts, labs, evidence register, and architecture detail.

Design 24-30 modules across exactly ten levels, from numerical foundations to
principal-architect decisions. Include level labs, measurable gates, memory and
capacity calculations, serving alternatives, enterprise architecture, and
learner-first cases. Verify key claims with free primary documentation.

Bootstrap consulted:
.copilot-tracking/research/subagents/2026-09-13/learning-plan-preparation-research.md.
HVE Markdown and writing-style instructions and repository build memory were read.
Module 1 is developed separately; avoid duplicating its full lesson here.

## Audience and learning contract

You already understand enterprise architecture, networking, cloud operations,
Kubernetes, and organizational constraints. The missing bridge is the behavior of
learned systems: why an update changes a model, why a benchmark can mislead, and
why a GPU fleet behaves differently from ordinary stateless services. Start with
those mechanisms, not Python syntax or another Kubernetes introduction.

The outcome is evidence-backed design competence across the lifecycle, not a
promise of research mastery or qualification to train frontier models. You should
be able to reproduce a small experiment, challenge a memory estimate, distinguish
model improvement from application improvement, and defend a production decision.
Large-scale training, security assurance, and principal-level judgment require
additional team experience, repeated incidents, and specialist review.

Module 1 receives a short contract and a minimal lab because its numerical lesson
is developed separately. All other modules build on that contract. A passing
gate permits progression; it does not certify every topic within the module.
Every threshold below is an educational acceptance criterion unless explicitly
identified as a mathematical invariant. Production thresholds require workload
evidence and accountable stakeholder approval.

Use a separate learning workspace and approved compute later. The bootstrap
reports that PyTorch is absent from the current ARISE-X virtual environment.
Nothing here installs it, executes workloads, or assumes existing GPU access.
Windows is suitable for reading and CPU exercises; later CUDA/NCCL and serving
exercises should use a supported Linux environment or a remote Linux GPU host.
Do not equate a Windows terminal with a supported distributed training platform.

## Why a measured concept-first sequence

| Approach | Strength | Limitation for this learner | Decision |
| --- | --- | --- | --- |
| Tool-first walkthroughs | Fast visible endpoint and early motivation | Conceals data leakage, optimizer state, token scheduling, and incompatible defaults | Use only as a short demonstration after a mechanism is understood |
| Pure theory-first course | Strong mathematical grounding | Delays operational feedback and can spend months on proofs unrelated to current decisions | Select derivations that explain an observable engineering behavior |
| Platform-first architecture | Reuses Kubernetes expertise immediately | Encourages treating weights as ordinary container assets and quality as uptime | Revisit existing skills after training and evaluation foundations |
| Measured stage-gated course | Connects a prediction, experiment, failure, and decision | Requires disciplined evidence capture rather than passive video completion | Recommended default |

Each cycle asks you to predict an outcome before execution, change one relevant
factor, measure both intended and unintended effects, and explain the discrepancy.
Keep a hypothesis ledger with a baseline, controls, data identity, precision,
hardware, seed, result, uncertainty, and decision. A negative result with a sound
diagnosis is a successful learning deliverable. A favorable chart without a valid
comparison is not. Reuse this ledger in architecture reviews and the capstone.

Read primary documentation narrowly: the optimizer contract during optimization,
the cache layout during memory planning, and the scaler contract during capacity
experiments. Do not memorize every framework option. Pin actual package versions
and model revisions when labs are implemented, since documentation aliases and
defaults move. Sources verified in this session are collected at the end.

## Workload and exact roadmap

There are 28 modules across exactly ten levels. Hours include reading, module
deliverables, the level lab, and one review. Labs are not additional hours to add
again. The 486-hour core assumes small models, bounded datasets, and existing
architecture skills. Reserve 20 percent, about 98 hours, for debugging and gate
retries: approximately 584 hours or 59-73 study weeks at 10-8 hours per week.
With holidays and work interruptions, plan roughly 15-19 calendar months. This is
an adjustable planning estimate, not a mastery guarantee or completion deadline.

| Level | Exact modules | Core hours | Study weeks at 8-10 hours |
| --- | --- | --- | --- |
| 1 foundations | 1 Numerical learning and experimental reasoning | 10 | 1.0-1.25 |
| 2 deep learning | 2 Neural networks and representation learning; 3 Optimization and training schedules; 4 Precision, memory, and reproducible training | 48 | 4.8-6.0 |
| 3 LLM internals | 5 Tokenization, embeddings, and language objectives; 6 Transformer tensor mechanics; 7 Autoregressive generation and context | 48 | 4.8-6.0 |
| 4 LLM training | 8 Pretraining data and compute strategy; 9 Distributed training and GPU fabrics; 10 Post-training objectives and reward learning | 56 | 5.6-7.0 |
| 5 fine-tuning | 11 Full fine-tuning and LoRA; 12 QLoRA, quantization, and alternative adapters; 13 Adaptation experiment design and transfer | 48 | 4.8-6.0 |
| 6 evaluation | 14 Model evaluation and statistical evidence; 15 Application, retrieval, and agent evaluation; 16 Safety, drift, and release qualification | 54 | 5.4-6.75 |
| 7 deployment | 17 Model artifacts and runtime selection; 18 Inference scheduling and GPU performance; 19 Serving contracts and delivery strategies | 54 | 5.4-6.75 |
| 8 LLMOps | 20 Lifecycle lineage and reproducible releases; 21 Observability and quality SLOs; 22 Feedback, incidents, and controlled improvement | 48 | 4.8-6.0 |
| 9 production platform | 23 Kubernetes GPU platform engineering; 24 Security, privacy, and tenant isolation; 25 Capacity, economics, and resilient placement | 56 | 5.6-7.0 |
| 10 principal architect | 26 Enterprise architecture and portfolio decisions; 27 Architecture assurance and organizational leadership; 28 Capstone design and evidence defense | 64 | 6.4-8.0 |

A weekly pattern is two hours of mechanism reading, four hours of experimentation,
two hours of interpretation, and up to two hours of review or catch-up. Do not
schedule more GPU work than you can inspect. Complete levels 1-3 before adaptation,
and complete level 6 before any external-user deployment. Basic held-out checks
begin in module 1; level 6 deepens them rather than introducing evaluation late.

Use CPU models for numerical and statistical work. A short rented or shared GPU
session can establish precision and serving behavior. Two or more GPUs are needed
to make measured claims about parallel scaling. Without that access, complete the
design and replay tracks but mark the distributed-performance gate pending.
Reading a published trace is not a substitute for a claimed local benchmark.

## Level 1 foundations

### Module 1 Numerical learning and experimental reasoning

Treat learning as an explicit numerical process rather than an API invocation.
Connect vectors, matrix multiplication, a scalar loss, and the chain rule to one
parameter update. Separate training examples from validation evidence and connect
probability estimates to decisions with asymmetric consequences. The goal is not
to repeat introductory programming; it is to establish the vocabulary required
to question every later experiment. Explain why reducing training loss does not
prove generalization, why a gradient is not a prediction, and why random seeds do
not guarantee cross-hardware reproducibility. Use one small regression example
whose forward pass and derivative can be checked by hand. Its full derivation and
worked lesson belong to the separately developed module 1 material, not here.

* Prerequisites: Algebra, basic functions, and ability to read short numerical code
* Suggested hours: 10
* Deliverable: One annotated forward-loss-backward-update trace and split rationale
* Gate: Hand and automatic gradients agree within 1e-5; explain three ways a lower training loss can mislead

### Lab 1 One auditable update

Objective and architecture: A CPU scalar regression calculation passes through
prediction, squared loss, derivative, and SGD update. No GPU, dataset download,
or orchestration is required. Prerequisites are module 1's separate lesson and a
later approved CPU PyTorch environment.

API sketch: `torch.tensor(..., requires_grad=True)`, `Tensor.backward()`,
`torch.optim.SGD`, `Optimizer.step()`, and `Optimizer.zero_grad()`.
Use x=2, y=4, w=1, loss=(wx-y)^2, and learning rate 0.1.

Expected output, unexecuted: Prediction 2, loss 4, gradient -8, updated weight
1.8, and new loss 0.16. Observe the old and new value separately rather than
printing a mutated reference. Repeat without clearing gradients and explain the
accumulation. The production equivalent is validating a training-loop contract
before expensive distributed execution. Pass with the module gate and identify
why one successful update says nothing about held-out quality.

## Level 2 deep learning

### Module 2 Neural networks and representation learning

A neural network learns intermediate representations that make a prediction task
easier, rather than relying entirely on hand-designed features. Compare a linear
baseline with a small multilayer perceptron and explain the role of nonlinear
activations, initialization, and residual paths. Relate cross-entropy to
classification and squared error to regression without assuming either metric
is the business objective. Use convolutional and recurrent models as contrasting
inductive biases, not as a detour into every architecture family. Track shapes
through layers and identify which parameters share information across positions.
Regularization, dropout, normalization, and early stopping should become
testable choices. A larger network may fit a noisy dataset better while providing
worse decisions; document that distinction through train-validation curves and
error slices rather than an architectural popularity contest.

* Prerequisites: Module 1
* Suggested hours: 14
* Deliverable: Linear versus MLP comparison with shape diagram and error slices
* Gate: Explain parameter counts exactly and attribute an overfitting curve to evidence rather than guessing

### Module 3 Optimization and training schedules

SGD follows sampled gradients; momentum smooths their history; Adam estimates
first and second moments; AdamW decouples weight decay from those moments. Work
through why these choices change update magnitude and state storage. Learning
rate is a policy over updates, not a universal property of a model. Compare warmup,
constant rate, and decay under a fixed token or example budget. Distinguish an
epoch, dataloader iteration, microbatch, optimizer step, and scheduler step.
Gradient accumulation changes the effective batch without making all examples
resident at once, but it is not automatically equivalent when normalization,
dropout, clipping, or loss weighting differs. Reason about noise and convergence
before increasing the batch to fill hardware. Interpret gradient norms and
learning curves together; elapsed epochs alone conceal differences in actual work.

* Prerequisites: Module 2
* Suggested hours: 18
* Deliverable: Controlled SGD, Adam, and AdamW runs with an update-count ledger
* Gate: Calculate effective batch and updates without ambiguity; reproduce large-batch versus accumulated FP32 gradients within 1e-5 on a controlled model

### Module 4 Precision, memory, and reproducible training

Precision is a set of choices for weights, activations, gradients, optimizer
states, and individual operations. Automatic mixed precision selects operation
dtypes; it does not mean every tensor becomes half precision or that a master
weight copy always exists. FP16 gradient scaling addresses underflow, while BF16's
different exponent range changes the tradeoff. Inspect actual tensor dtypes and
optimizer state after the first step. Distinguish allocated tensors, allocator
reservations, device context, temporary workspaces, and checkpoint storage.
Activation checkpointing trades recomputation for retained activations and can
change runtime behavior. Reproducibility requires data order, transforms, random
state, scheduler, and optimizer state as well as weights. Learn to explain a
resume discrepancy before promising bitwise replay across software or hardware
changes. The official AMP examples support the accumulation and clipping order.

* Prerequisites: Module 3
* Suggested hours: 16
* Deliverable: Precision and memory ledger plus interrupted/resumed training comparison
* Gate: Account for all persistent tensor categories; diagnose one nonfinite-gradient case and one incorrect resume

### Lab 2 Training under a fixed work budget

Objective: Separate optimization effects from systems effects. Architecture:
a synthetic two-class dataset feeds a linear baseline and a two-layer MLP,
then a metrics collector records optimizer updates, loss, elapsed time, and memory.
Prerequisites are modules 1-4, CPU PyTorch, and an optional supported GPU for AMP.
Use 1,024 examples, a fixed train-validation split, and a no-dropout,
no-batch-normalization model for the accumulation equivalence test.

Exact API surface: `torch.nn.Linear`, `torch.nn.ReLU`,
`torch.nn.functional.cross_entropy`, `torch.optim.SGD`, `torch.optim.Adam`,
`torch.optim.AdamW`, `torch.autocast`, `torch.amp.GradScaler`, and
`torch.nn.utils.clip_grad_norm_`. Inspect `Optimizer.state_dict()` and use
`torch.cuda.max_memory_allocated()` only on the GPU track.

```text
For each effective batch of 64 examples:
	clear gradients once
	process four equal microbatches of 16
	backpropagate each mean loss divided by four
	if FP16 scaling is enabled, unscale once after all four backwards
	clip once, apply one optimizer update, update scaler once
	advance the update-based scheduler only after a successful update
	record update count, examples seen, rate, gradient norm, and loss
```

First compare one batch of 64 with four batches of 16 in FP32. Then sweep three
learning rates for each optimizer with the same number of examples seen. Finally,
interrupt at an effective-batch boundary, persist the complete training state,
and resume. Expected output, unexecuted: Matched controlled gradients, distinct
optimization curves, a state inventory, and a resume comparison. No optimizer is
expected to win universally.

Observe underflow, skipped FP16 updates, a wrong loss divisor, clipping before
unscale, and missing scheduler state. Use a deliberately incomplete final
accumulation group to explain why division by four can be wrong. Production
equivalent: Diagnose a costly training regression before changing fleet size.
Pass when equivalence meets tolerance and all introduced faults are identified.

## Level 3 LLM internals

### Module 5 Tokenization, embeddings, and language objectives

An LLM predicts over token IDs, not words or raw business concepts. Examine how
byte-pair or related subword tokenization changes sequence length for English,
code, identifiers, and multilingual text. Embedding lookup converts IDs into
learned vectors; it is not the same operation as producing a sentence embedding
for retrieval. Connect next-token cross-entropy to a shifted target sequence and
explain the roles of padding masks and loss masks. Chat formatting is part of
the model contract: role delimiters, beginning/end tokens, and generation prompts
can alter behavior even when visible text looks identical. Compare a base model
with an instruction-tuned model without changing the tokenizer accidentally.
Vocabulary size affects embedding and output-projection storage; tokenization
also changes billing, context usage, throughput, and evaluation comparability.

* Prerequisites: Modules 2-4
* Suggested hours: 14
* Deliverable: Token and label inspection for 30 domain examples and two templates
* Gate: Detect duplicate special tokens and off-by-one labels in all seeded fixtures; explain why cross-tokenizer perplexities are not directly comparable

### Module 6 Transformer tensor mechanics

Trace a decoder block from batch-by-sequence-by-hidden input to vocabulary
logits. Queries, keys, and values are learned projections, with separate head
counts under grouped-query attention. Scaled dot products, causal masking,
softmax, and value aggregation mix earlier positions; the feed-forward network
transforms each position's features. Residual connections and normalization
control information and gradient flow. RoPE rotates query/key components by
position rather than appending a position label to the output. Contrast RMSNorm
with LayerNorm and a gated FFN with a basic two-layer MLP. Calculate intermediate
shapes before inspecting tensors. Mathematical attention scores have quadratic
sequence dimensions, but optimized attention can avoid materializing that entire
matrix. Do not confuse a pedagogical score tensor with the memory layout of a
production attention kernel or claim RoPE alone guarantees long-context quality.

* Prerequisites: Module 5 and matrix multiplication from module 1
* Suggested hours: 20
* Deliverable: Annotated GQA decoder block with parameter and activation shapes
* Gate: Derive every shape for B=2, T=16, D=256, Hq=8, Hkv=2, head_dim=32; pass a causal-invariance test

### Module 7 Autoregressive generation and context

Generation repeatedly evaluates a conditional distribution, chooses a token,
and extends context. Distinguish raw logits from probabilities and compare
greedy selection, temperature, top-k, and top-p sampling. Stopping rules and
maximum output length affect both user experience and evaluation results. KV
caching preserves past keys and values to avoid recomputing them, but it adds
memory proportional to retained context and active sequences. Prefill processes
the prompt; decode extends it incrementally. Long-context support is therefore
both a numerical/model capability and a scheduling constraint. Test retrieval
from different positions, not only whether a long input is accepted. Compare
cached and uncached generation with matched settings and tolerances. Explain
why deterministic sampling settings do not eliminate all hardware-dependent
numerical differences, and why streaming is transport behavior rather than a
different learned objective.

* Prerequisites: Module 6
* Suggested hours: 14
* Deliverable: Generation trace showing logits, selected tokens, cache growth, and stopping decisions
* Gate: Reconcile cache and non-cache outputs on a tiny model; separate time to first token from inter-token latency

### Lab 3 A decoder you can explain

Objective: Expose the tensor and cache contracts without downloading a large
checkpoint. Architecture: Synthetic IDs enter a tiny randomly initialized
Llama-style causal model; hooks capture projection shapes, while a second path
computes a reference causal attention operation. Prerequisites are modules 5-7
and CPU PyTorch plus Transformers in a later dedicated environment. Random
weights are adequate because the objective is mechanics, not language quality.

Exact APIs: `transformers.LlamaConfig(vocab_size=128, hidden_size=256,
intermediate_size=512, num_hidden_layers=2, num_attention_heads=8,
num_key_value_heads=2, max_position_embeddings=256)`;
`transformers.LlamaForCausalLM(config)`; `Module.register_forward_hook()`;
`model(input_ids=ids, labels=ids, use_cache=False)`;
`model(input_ids=prefix, use_cache=True)`; and the returned `past_key_values`
cache passed to a subsequent model call. Pass a valid attention mask and
position information for the combined cache and new token per the pinned API.

For B=2 and T=16, explain hidden states of shape (2,16,256), query projections
(2,16,256), key/value projections (2,16,64), queries reshaped to (2,8,16,32),
and unexpanded keys/values (2,2,16,32). Each group of four query heads shares
one KV head. Conceptual attention scores are (2,8,16,16); final logits are
(2,16,128). The FFN intermediate dimension is 512 for both gate and up paths.

Expected output, unexecuted: A shape ledger, finite loss, and next-token logits
matching cached versus full-prefix computation within a chosen FP32 tolerance.
Change only future tokens and confirm earlier logits remain invariant in eval
mode. Observe faults from incorrect mask polarity, cache positions, and labels
shifted twice. A low loss from looking ahead is leakage, not intelligence.
Production equivalent: Debug a model conversion, cache backend, or context-window
regression. Pass the module shape gate and retain a failing and repaired trace.

## Level 4 LLM training

### Module 8 Pretraining data and compute strategy

Pretraining from random initialization learns broad token statistics; continued
pretraining adapts an existing model to another distribution, often without
instruction labels. Both require data rights, provenance, filtering, deduplication,
and independent evaluation. Design a token mixture across domains and languages,
then distinguish mixture weights from an ordered learning curriculum. Synthetic
data can add targeted coverage but can also amplify teacher errors, duplicated
reasoning, and benchmark contamination. Measure diversity and verification cost,
not only generated token count. Use scaling-law research to form hypotheses
about model size, tokens, and compute, while recognizing that compute-optimal
pretraining is not necessarily lifecycle-cost-optimal serving. Continued training
can erase useful capabilities. Compare a domain-only mixture with replay of
general data, and budget checkpointing, retries, preprocessing, and evaluation
alongside accelerator time rather than treating FLOPs as the complete bill.

* Prerequisites: Modules 1-7
* Suggested hours: 20
* Deliverable: Versioned corpus manifest, mixture experiment, and compute budget
* Gate: Trace every data shard to a permitted source; distinguish duplicate-free splits from unproven absence of pretraining contamination

### Module 9 Distributed training and GPU fabrics

Map each parallel technique to the tensors it partitions and the messages it
creates. Data parallelism processes different examples; FSDP or ZeRO shards
training state. Tensor parallelism splits operations, pipeline parallelism splits
layers, sequence parallelism can shard normalization/residual activations, and
context parallelism partitions long-sequence work across attention. Expert
parallelism routes tokens to MoE experts, so load balance and all-to-all traffic
matter even when active parameter count is small. HBM capacity, memory bandwidth,
FLOPs, PCIe, NVLink, and inter-node InfiniBand or RoCE constrain different phases.
NCCL collectives require matching participation and compatible shapes across
ranks. A larger fleet can reduce useful throughput when communication dominates.
Sketch the device mesh, place frequent communication on faster links, and
measure scaling efficiency before recommending another dimension of parallelism.

* Prerequisites: Modules 4, 6, and 8; existing network architecture knowledge
* Suggested hours: 20
* Deliverable: DP/TP/PP/SP/CP/EP mapping with a measured two-rank collective trace or explicitly pending hardware evidence
* Gate: Explain all-reduce, all-gather, reduce-scatter, and all-to-all; identify one topology and one rank-participation failure

### Module 10 Post-training objectives and reward learning

Supervised fine-tuning teaches behavior from demonstrations; preference learning
uses comparisons rather than assuming one reference answer is uniquely correct.
Traditional RLHF commonly combines SFT, a learned reward model, and policy
optimization with a reference-policy constraint. DPO optimizes preference pairs
directly and does not require a separately trained reward model in its standard
form. GRPO generates groups of completions and derives relative advantage from
rewards; it moves cost into rollout generation and reliable reward computation.
Reward can be learned, human-provided, or mechanically verifiable, and each has
blind spots. Study reward hacking, length bias, zero-variance groups, and policy
collapse. Keep reward improvement separate from held-out task improvement.
Implementation defaults evolve, so explicitly choose normalization, reference
behavior, and loss variant rather than treating every GRPO implementation as the
original paper's algorithm.

* Prerequisites: Modules 3, 7, and 8
* Suggested hours: 16
* Deliverable: SFT/RLHF/DPO/GRPO decision record and audited toy reward/preference dataset
* Gate: Explain which objects require gradients in each method and reject a deliberately reward-hacked candidate using independent evidence

### Lab 4 A miniature training program with a restart

Objective: Exercise the training lifecycle at toy scale and account for what
cannot be inferred about frontier training. Architecture: Two permitted synthetic
text domains feed a fixed tokenizer, a tiny causal model, a checkpoint store,
and a held-out evaluator. A separate preference/reward worksheet compares
post-training objectives. Prerequisites are level 3's tiny model, module 8's
data manifest, and optional access to two Linux GPUs for a distributed branch.

Exact API surface: `datasets.Dataset.from_dict`,
`transformers.AutoModelForCausalLM.from_config`, `torch.optim.AdamW`,
`model.save_pretrained`, optimizer/scheduler `state_dict`,
`torch.distributed.init_process_group`, `torch.distributed.all_reduce`, and
`torch.nn.parallel.DistributedDataParallel`. GPU processes must each select
their assigned device; use NCCL only on the supported GPU track. CPU collective
simulation uses an appropriate CPU backend and is not an NCCL benchmark.

Run 100 bounded updates from random initialization, then 50 continued updates
on domain B. Compare a domain-only continuation with a mixture retaining domain
A. Split by document family before token packing. Save model, optimizer,
scheduler, seed/RNG, sampler/data cursor, and update count at update 75; resume
from that boundary and compare with the uninterrupted path. In the two-rank
branch, verify a sum all-reduce of rank values 1 and 2 returns 3 on both ranks.

Create ten preference pairs with explicit prompt/chosen/rejected fields for
`trl.DPOTrainer`. Separately score groups of four generated answers with a
deterministic arithmetic checker accepted by `trl.GRPOTrainer(reward_funcs=...)`.
Compute advantages on paper, including an all-equal-reward group. Training these
post-training variants is optional; analyzing their data and memory contracts is
required and included in the hours.

Expected output, unexecuted: Corpus lineage, loss slices for both domains,
resume agreement within the declared tolerance, and a reward failure table.
Observe catastrophic forgetting, duplicated data, missing sampler state, and a
missing collective participant. Production equivalent: A restartable training
program with credible data and reward governance. Pass when no evaluated record
is in the toy training split and each restart discrepancy is explained.

## Level 5 fine-tuning

### Module 11 Full fine-tuning and LoRA

Full fine-tuning updates the selected base parameters and typically creates
gradients and optimizer state for a large fraction of the model. LoRA freezes
base weights and learns a low-rank update, usually represented as two smaller
matrices. Derive the extra parameter count before selecting rank and target
modules. The saving is primarily trainable state; forward computation and
activation storage do not disappear. Compare attention-only targets with wider
linear-layer coverage under a matched task and work budget. Distinguish the
training objective, such as SFT or DPO, from the update mechanism, such as LoRA.
They are independent choices. Merging an adapter changes the artifact and may
change numerical behavior, especially around quantization. Preserve the exact
base revision and tokenizer contract, and evaluate the deployed representation
rather than assuming the training checkpoint is operationally interchangeable.

* Prerequisites: Level 4
* Suggested hours: 18
* Deliverable: Full-update versus LoRA experiment with trainable parameter and peak-memory counts
* Gate: Predict LoRA parameter count exactly for selected linear layers; show frozen parameters receive no updates

### Module 12 QLoRA, quantization, and alternative adapters

QLoRA combines a quantized frozen base with trainable low-rank parameters; it is
not full-model integer training. Distinguish storage precision, compute precision,
quantization scales, and optimizer precision. Post-training quantization can
reduce deployment cost but depends on representative calibration, kernel support,
and acceptable quality change. Compare weight-only INT8/INT4, floating-point
low-precision formats, and quantized KV caches without assuming equal support
or speed. Alternative parameter-efficient methods modify different surfaces:
bottleneck adapters insert modules, prompt tuning learns input embeddings, prefix
tuning adds learned attention prefixes, and IA3 rescales activations with learned
vectors. Their serving implications differ, particularly context overhead,
merging, and multi-adapter batching. Choose based on task evidence and runtime
support, not the smallest checkpoint alone. Keep a compatibility matrix tied to
the actual model, accelerator, library versions, and export path.

* Prerequisites: Modules 4 and 11
* Suggested hours: 16
* Deliverable: QLoRA experiment and a full FT/LoRA/QLoRA/adapters/prefix/prompt/IA3 comparison
* Gate: Reconcile quantization metadata with storage estimates and demonstrate an agreed held-out quality bound after conversion

### Module 13 Adaptation experiment design and transfer

Decide whether the task needs new knowledge, a better interface, a constrained
output, or a changed behavior before reaching for training. Retrieval can supply
fresh authorized evidence; prompting can clarify instructions; SFT can teach
formats; continued pretraining can shift domain statistics. These approaches
solve overlapping but different problems. Build a baseline ladder that compares
them against the same held-out questions and includes human escalation or no
model as legitimate outcomes. Audit synthetic demonstrations for teacher errors,
copied answers, and coverage gaps. Track learning curves by data volume and
evaluate general-capability retention as well as domain improvement. Test adapter
transfer to a new base revision as an explicit compatibility experiment rather
than a routine upgrade. Record the cheapest intervention that satisfies the
requirement and the evidence that would justify a more expensive one.

* Prerequisites: Modules 8, 10-12
* Suggested hours: 14
* Deliverable: Adaptation decision record with prompt, retrieval, and fine-tuned baselines
* Gate: Use a locked split and fixed budget; defend selection or rejection without relying on training loss

### Lab 5 Adapt a model without losing its identity

Objective: Compare a base checkpoint, a prompt baseline, and a LoRA adaptation
on a narrow formatting task. Architecture: An approved local small causal model
and tokenizer consume synthetic ticket summaries; a training runner emits an
adapter; an evaluator tests both domain formatting and general retention.
Prerequisites are level 4, a permitted 100M-1B-class model selected for available
memory, PEFT, Transformers, and a reviewed dataset of 200 training and 100 held-out
items. These counts support learning, not high-confidence production claims.

Exact APIs: `peft.LoraConfig(r=8, lora_alpha=16, target_modules=["q_proj",
"v_proj"], bias="none", task_type="CAUSAL_LM")`, `peft.get_peft_model`,
`PeftModel.save_pretrained`, and `PeftModel.from_pretrained`. Inspect the chosen
model's actual module names before applying this Llama-style target list.
For the optional QLoRA branch, use `transformers.BitsAndBytesConfig` with
`load_in_4bit=True`, `bnb_4bit_quant_type="nf4"`,
`bnb_4bit_compute_dtype=torch.bfloat16`, and
`peft.prepare_model_for_kbit_training` on supported hardware.

Compute target counts, hash frozen weights before and after training, and inspect
loss masks on ten examples. Save the adapter with the base revision, tokenizer,
template, training data digest, and evaluation digest. Reload in a fresh process
and compare against the training-time model. Do not require merging into a
quantized base when the selected backend does not support it. Compare full
fine-tuning on a smaller toy model if the real checkpoint exceeds the budget.

Expected output, unexecuted: Trainable parameter inventory, unchanged base-weight
hashes, reload parity, and paired quality results. Choose an educational bound
before training, such as no more than a five-percentage-point retention loss;
report uncertainty rather than declaring the bound statistically proven from
100 examples. Observe wrong targets, missing adapters, tokenizer changes,
unsupported quantization, and schema-valid but incorrect answers. Production
equivalent: A governed adapter release with an independently tested base binding.
Pass with exact identity checks and a justified adaptation decision.

## Level 6 evaluation

### Module 14 Model evaluation and statistical evidence

Model evaluation isolates capabilities under a controlled prompt and generation
protocol. Use perplexity for compatible tokenization/objective comparisons and
task metrics for the behavior that matters. Benchmark scores are samples, not
immutable properties of a checkpoint. Separate data leakage from potential
pretraining contamination, and state when the latter cannot be ruled out.
Use paired comparisons on the same independent tasks, confidence intervals,
effect sizes, and predeclared practical margins. Resample at the task or customer
cluster level when repeated turns are dependent. Human evaluation needs a rubric,
blind assignment, disagreement handling, and protected reviewer conditions.
LLM-as-judge evaluations need calibration against humans and checks for position,
verbosity, and self-preference biases. Repeating a biased judge many times does
not fix bias. Distinguish inconclusive evidence from evidence of equivalence and
avoid tuning repeatedly against the final holdout.

* Prerequisites: Modules 1, 7, and 13
* Suggested hours: 18
* Deliverable: Paired model report with confidence intervals, rubric, contamination statement, and blind labels
* Gate: Reproduce the interval from raw task records; explain why a statistically significant but negligible effect may not justify release

### Module 15 Application, retrieval, and agent evaluation

An application combines model behavior with retrieval, prompts, tools, policies,
and user state. Evaluate retrieval recall and authorization separately from
answer grounding and task completion. A correct answer drawn from another
tenant's documents is still a failure. Agent evaluation must inspect sequences
of decisions, tool arguments, side effects, retries, and stop conditions, not
only the final message. Long-context tests should vary evidence position,
distractors, conflicting instructions, and multi-hop dependencies. Tool tests
need executable contracts and sandbox state assertions. Pair human or judge
assessments with deterministic checks where possible, and distinguish schema
validity from semantic correctness. Estimate cost and time per completed task
across the whole trajectory. A stronger model can produce a worse agent when
it makes unnecessary calls, ignores policy boundaries, or becomes overconfident
after a partial tool failure.

* Prerequisites: Module 14 and existing API architecture knowledge
* Suggested hours: 18
* Deliverable: Layered model/retrieval/application/agent evaluation suite with trajectory records
* Gate: Attribute ten seeded failures to the correct layer and verify side effects independently of generated claims

### Module 16 Safety, drift, and release qualification

Production qualification combines quality evidence with safety, privacy,
reliability, and operational limits. Define unacceptable outcomes as explicit
constraints instead of averaging them away inside a single score. Distinguish
input distribution drift, label/concept drift, retrieval-corpus changes,
behavioral regression, and evaluator drift. A changed input distribution is a
reason to investigate, not proof that retraining is required. Compare cohorts
and time windows with stable definitions, and account for delayed feedback.
Safety evaluation needs representative misuse and accidental-failure scenarios,
refusal quality, and authorized escalation paths. Assess long-context injection
and tool boundary violations in controlled fixtures without exposing real
systems. Release qualification must fail closed when provenance, sample size,
or mandatory tests are missing. Define what can be approved, what must be
rejected, and what remains inconclusive with a named decision owner.

* Prerequisites: Modules 14-15
* Suggested hours: 18
* Deliverable: Release gate policy and drift investigation matrix
* Gate: Mandatory failures cannot be offset by aggregate gains; missing evidence produces an explicit non-pass result

### Lab 6 A release decision that can say inconclusive

Objective: Distinguish model, application, and agent evidence while controlling
comparison bias. Architecture: Two candidate releases answer the same 100
synthetic tasks; deterministic checkers, a blind human rubric, and an optional
judge produce task-level records; a statistical layer emits a release decision.
Prerequisites are level 5 artifacts, a locked test split, two reviewers where
available, and SciPy for the later executable version. A single learner can
complete the mechanics, but independent human agreement remains pending.

Exact statistical API: `scipy.stats.bootstrap((candidate, baseline), statistic,
paired=True, confidence_level=0.95, n_resamples=9999, method="BCa", rng=42)`.
The statistic returns the mean task-score difference. Pairing requires aligned
task IDs, not merely equal array lengths. When multiple turns belong to one
task, aggregate first or implement cluster resampling. Handle degenerate
intervals and missing values explicitly rather than coercing them to passes.

Create separate measures for model correctness, retrieval evidence recall,
grounded answer accuracy, tool argument validity, verified state change, and
end-to-end cost. Reverse A/B presentation on half the judge items. Place the same
evidence at early, middle, and late positions in long-context cases. Seed a
train/test duplicate, ten malformed tool calls, one unauthorized retrieval, and
a shifted input cohort. Human reviewers adjudicate a small blind subset and
record disagreement rather than forcing artificial consensus.

Expected output, unexecuted: A paired interval, judge-human disagreement table,
layered failure taxonomy, and PASS/FAIL/INCONCLUSIVE decision. An example policy
requires a positive lower confidence bound for improvement, all mandatory
privacy tests passing, and complete provenance; these are chosen lab rules,
not universal enterprise thresholds. Observe judge position bias, duplicate
inflation, mismatched task ordering, and an aggregate gain hiding a safety loss.
Production equivalent: Qualification evidence for an accountable release board.
Pass when every seeded integrity or mandatory-policy fault prevents promotion.

## Level 7 deployment

### Module 17 Model artifacts and runtime selection

A deployable model is more than a weight file. Package configuration, tokenizer,
chat template, generation defaults, adapters, quantization metadata, licenses,
and evaluation evidence with immutable identities. Distinguish a registry's
approval metadata from an object store's bytes and from a container registry's
runtime image. Serving options occupy different layers: vLLM provides optimized
LLM execution and APIs; Triton Inference Server manages model backends and
scheduling; TensorRT-LLM targets NVIDIA LLM inference; ONNX is an interchange
format with runtimes such as ONNX Runtime. TGI remains relevant to existing
estates but its official documentation now says maintenance mode. Current
TensorRT-LLM documentation also changes older engine-build assumptions. Compare
model support, accelerator compatibility, debugging, upgrades, and reproducible
performance before selecting a runtime. The decision must include an exit path,
not merely the best advertised throughput figure.

* Prerequisites: Levels 5-6
* Suggested hours: 16
* Deliverable: Content-addressed model bundle and runtime decision matrix
* Gate: Reconstruct the exact release from immutable references and reject a missing tokenizer or incompatible adapter

### Module 18 Inference scheduling and GPU performance

Inference performance depends on the request distribution and scheduling policy,
not only GPU count. Prefill processes many prompt tokens together and often
offers substantial compute parallelism; decode repeatedly reads weights and
growing KV state for new tokens and can be bandwidth constrained. Continuous
batching admits new work as other sequences finish. Paged KV allocation reduces
fragmentation but does not remove the bytes required for useful context.
Speculative decoding trades draft computation and verification for fewer target
iterations; benefit depends on acceptance rate and workload. Tensor parallelism
can improve fit or latency while adding communication. Measure time to first
token, inter-token latency, output throughput, queue time, and goodput under an
SLO. Study HBM bandwidth, FLOPs, PCIe/NVLink topology, and cache occupancy together
before concluding that high utilization indicates efficient service.

* Prerequisites: Modules 7, 9, and 17
* Suggested hours: 22
* Deliverable: Prompt/output-length load matrix and bottleneck diagnosis
* Gate: Predict memory-limited concurrency and explain measured saturation; report SLO-qualified goodput rather than raw tokens alone

### Module 19 Serving contracts and delivery strategies

Online synchronous requests, offline batch jobs, asynchronous queued work, and
streaming responses have different admission, retry, and cancellation contracts.
Streaming can improve perceived responsiveness while leaving total completion
time unchanged. Define bounded queues, deadlines, idempotency for side effects,
and what happens when a client disconnects mid-generation. Separate rollout
mechanics from experimental design: blue-green swaps environments, canary limits
exposure, shadow duplicates selected traffic without returning candidate answers,
and A/B tests compare randomized cohorts. Champion-challenger is a model-governance
relationship that can use several delivery mechanisms. Keep stable capacity
available for rollback and bind model, prompt, adapter, retrieval index, and
runtime versions in one release. Tool side effects must never execute twice
because of shadowing. Kubernetes Services alone do not provide precise weighted
or mirrored traffic; use a verified routing integration when needed.

* Prerequisites: Modules 16-18
* Suggested hours: 16
* Deliverable: Serving API contract and blue-green/canary/shadow/A-B rollback plan
* Gate: Demonstrate bounded overload, cancellation, and consistent release identity with no duplicated sandbox side effects

### Lab 7 Load-test an immutable serving candidate

Objective: Find the first limiting resource and validate a rollback-safe serving
contract. Architecture: A load generator reaches an authenticated gateway,
which routes to stable and candidate vLLM services; metrics and an offline
evaluator collect evidence. Prerequisites are a Linux host with supported GPU,
an approved small model bundle, a pinned vLLM runtime, and a private lab network.
Use one engine at a time if memory cannot hold both; that supports benchmarking
but does not complete the simultaneous rollback-capacity experiment.

Verified API surface: `GET /v1/models`, `GET /health`, `GET /metrics`,
`POST /v1/completions`, and `POST /v1/chat/completions` where a valid chat
template exists. The implementation later starts the documented `vllm serve`
entry point with an immutable local model path and explicit context limits.
Use the compatible request contract below; this is unexecuted HTTP sketching,
not a command issued in this workspace.

```http
POST /v1/chat/completions HTTP/1.1
Content-Type: application/json

{"model":"lab-candidate","messages":[{"role":"user","content":"Summarize the supplied synthetic ticket."}],"max_tokens":64,"temperature":0,"stream":true}
```

Sweep prompt lengths 128, 1,024, and 4,096 tokens, output caps 32 and 256, and
concurrency 1, 2, 4, and 8 within safe memory limits. Run cold and warm cases
separately. Record actual output lengths, warmup policy, offered load, completed
load, errors, queue times, first-token latency, inter-token latency, and peak
memory. Cancel one stream and verify resources are released. Use a gateway
request budget rather than exposing the engine's administrative endpoints.

Expected output, unexecuted: A performance matrix and a capacity boundary, not
a predetermined tokens-per-second result. Introduce an invalid template,
oversized prompt, saturated queue, and candidate quality regression. Observe
that HTTP health can pass while answer quality fails. Shadow only read-only
tasks, then exercise a candidate traffic cutback with draining. Production
equivalent: A runtime qualification and release rehearsal. Pass when overload is
bounded, all outcomes carry a release identity, and the rollback respects the
declared lab recovery objective without assuming live KV migration.

## Level 8 LLMOps

### Module 20 Lifecycle lineage and reproducible releases

MLOps coordinates data, training, evaluation, and deployment. LLMOps extends the
release identity to prompts, chat templates, retrieval indexes, quantization,
judges, and model dependencies. AgentOps adds tool schemas, permissions,
environment state, trajectories, and action policies. Treat these as overlapping
operating responsibilities rather than three unrelated product categories.
Create a dependency graph that connects every serving release to its data and
evaluation evidence. CI validates deterministic contracts and artifact integrity;
expensive statistical evaluations run in controlled pipelines; CD promotes only
approved bundles. GitOps reconciles declared runtime state but cannot infer
model quality from a manifest. Keep training credentials separate from release
approval and serving identities. A rollback must restore compatible components,
not just an earlier container image. Record intentionally nondeterministic
elements and the limits of replay rather than promising impossible reproducibility.

* Prerequisites: Levels 6-7
* Suggested hours: 16
* Deliverable: Release manifest and lineage graph across data, model, prompts, tools, and evaluators
* Gate: Identify every upstream dependency for two releases and block promotion when any mandatory digest or approval is absent

### Module 21 Observability and quality SLOs

Traditional request telemetry explains latency and errors but not whether an
answer helped the user. Connect infrastructure metrics, inference scheduling,
application traces, and delayed quality labels through bounded identifiers.
OpenTelemetry provides transport and instrumentation patterns; GenAI semantic
conventions are evolving and must be versioned rather than assumed permanently
stable. Separate request availability, first-token latency, completion latency,
grounded quality, and successful task completion into interpretable objectives.
Define populations and measurement windows, including exclusions for invalid
requests and missing labels. Token counts and cost are useful but do not measure
correctness. Avoid high-cardinality prompt text in metric labels and avoid
capturing sensitive content by default. Use sampled, authorized evidence when
diagnosis needs text. Correlate a quality drop with prompt, retrieval, model,
and runtime changes before treating it as a GPU problem.

* Prerequisites: Modules 15, 18, and 20
* Suggested hours: 18
* Deliverable: Trace schema, privacy policy, dashboard design, and quality SLO definitions
* Gate: Locate a seeded latency or quality regression from correlated evidence while exporting no raw confidential fixture content

### Module 22 Feedback, incidents, and controlled improvement

Feedback is not automatically a training label. Users may abandon tasks, provide
ambiguous ratings, or report outcomes long after generation; a feedback pipeline
must preserve consent, provenance, and context. Separate an incident response
from a model-improvement program. Rollback, traffic restriction, tool disablement,
or human escalation may be safer than retraining during an outage. Route
suspected drift through evidence collection and a repeatable evaluation before
changing datasets or rewards. Postmortems should connect failure mechanisms to
preventive tests and owner actions without claiming that one new test prevents
all recurrences. Keep incident evidence out of training until privacy review and
split rules permit reuse. Measure whether a remedial change improves the intended
cohort and whether it regresses another. Close the loop through an approved
release, not through an uncontrolled online learning path.

* Prerequisites: Modules 16 and 20-21
* Suggested hours: 14
* Deliverable: Feedback triage workflow, incident runbook, and regression-test proposal
* Gate: Classify five feedback records correctly and contain a simulated incident without unauthorized model or data updates

### Lab 8 Correlate a bad answer to a release

Objective: Connect a model-service trace with quality evidence and a controlled
remediation. Architecture: Gateway and application spans connect retrieval,
generation, sandbox tools, and a delayed evaluation event; an OpenTelemetry
collector exports redacted telemetry; a release registry resolves identities.
Prerequisites are level 7, a local or remote telemetry sandbox, synthetic
nonpersonal data, and an explicit retention policy.

Exact instrumentation APIs: `opentelemetry.trace.get_tracer`,
`Tracer.start_as_current_span`, `Span.set_attribute`, `Span.record_exception`,
and W3C `traceparent` propagation. A later setup supplies the SDK tracer provider
and exporter; the API alone is a no-op without configuration. Use core tracing
plus organization-owned attributes such as `arise.release.id` until the selected
GenAI semantic-convention version has been approved. OTLP transport is a standard
integration boundary, not permission to export raw prompts.

```text
gateway span
	application span [release id, approved task class]
		retrieval span [index digest, hit count, authorization result]
		generation span [model digest, token counts, timing]
		tool span [schema digest, policy result, sandbox outcome]
later evaluation event [task evidence id, rubric version, result]
```

Introduce three changes separately: a retrieval index missing a document, a
prompt-template regression, and a slow tool. Keep model weights identical.
Demonstrate why a model-version-only dashboard cannot distinguish the first
two. Send delayed quality labels through a bounded join key, and show how
missing labels affect the SLO denominator. Verify that metric dimensions use
bounded release/task categories rather than unique prompts or request IDs.

Expected output, unexecuted: Three distinguishable traces, one delayed quality
join, a privacy scan, and a rollback recommendation. Observe lost propagation,
collector failure, evaluator version drift, and accidental text export. The
telemetry pipeline must degrade without blocking every inference request.
Production equivalent: A quality incident investigation across platform and
application ownership. Pass when a reviewer can find the responsible component
from evidence and sensitive canary strings never appear in exported payloads.

## Level 9 production platform

### Module 23 Kubernetes GPU platform engineering

GPU scheduling requires compatible drivers, container runtime integration, and
a device plugin or other supported resource allocation path. An operator can
manage those components, but it does not erase upgrade compatibility or security
review. Extended GPU resources are not ordinary CPU overcommit; inspect requests,
limits, node labels, taints, tolerations, and topology. MIG partitions supported
hardware, whereas time slicing shares a device without equivalent memory/fault
isolation. Build separate policies for experiments, online inference, and
distributed training. KEDA scales workloads from event metrics; the node
autoscaler addresses unschedulable capacity, and neither makes model loading
instantaneous. Weight caching, storage bandwidth, readiness checks, and graceful
draining dominate many cold-start incidents. Measure a full path from requested
replica to usable tokens, and ensure multi-GPU replica placement preserves the
communication assumptions used in earlier benchmarks.

* Prerequisites: Modules 9, 18-21 and existing Kubernetes operations skills
* Suggested hours: 20
* Deliverable: GPU pool and scheduling design with cold-start measurements
* Gate: Diagnose pending, driver, cache, and readiness faults separately; explain why time-sliced resource count is not physical GPU capacity

### Module 24 Security, privacy, and tenant isolation

An LLM platform accepts untrusted data at multiple boundaries: training corpora,
retrieved documents, prompts, tool results, checkpoints, and runtime packages.
Separate data content from control authority, and enforce tool permissions
outside the model. Protect corpus ingestion against poisoning with provenance,
review, deduplication, and evaluation, while recognizing that none proves a
dataset harmless. Secure the software and model supply chain through pinned
artifacts, signatures, controlled builders, dependency review, and verification
at admission. Limit registry writes, training access, serving identities, and
release approvals with distinct RBAC roles. Namespace separation alone is not
a hard boundary for hostile tenants sharing a kernel or GPU. Include retrieval
ACLs, cache keys, logs, quotas, and deletion workflows in tenant design. Privacy
requirements apply to prompts, responses, traces, embeddings, adapters, and
backups, not only the source database.

* Prerequisites: Modules 15-16, 20, and 23
* Suggested hours: 18
* Deliverable: Threat model with data/control boundaries and tenant-isolation tests
* Gate: All cross-tenant retrieval/cache/tool fixtures fail closed; unapproved artifacts cannot reach serving

### Module 25 Capacity, economics, and resilient placement

Capacity combines memory fit, token throughput, queue stability, latency,
availability, and the distribution of input/output lengths. Use Little's Law
within a clearly defined boundary, then load-test burst behavior rather than
deriving tail guarantees from averages. Compare small-model routing, semantic
caching, exact-prefix reuse, and batching with their quality and privacy costs.
Multi-tenant fairness requires admission budgets and scheduling, not just
per-namespace GPU quotas. Model cloud, on-premises, and air-gapped placement using
utilization, staffing, support, power, egress, reserved headroom, and recovery
capacity. Define RTO/RPO separately for artifacts, indexes, session state, and
audit evidence. A replicated weight file does not create a warm failover service.
Validate degraded modes and recovery dependencies, and avoid synchronous
cross-region tensor parallelism as a default substitute for independent regional
replicas.

* Prerequisites: Modules 18-19 and 23-24
* Suggested hours: 18
* Deliverable: Capacity workbook, fictional cost sensitivity analysis, and DR matrix
* Gate: Reconcile memory and throughput limits, include failure headroom, and defend a placement decision across three demand scenarios

### Lab 9 A GPU service survives platform friction

Objective: Validate the interaction between pod scaling, node capacity, model
loading, and tenant boundaries. Architecture: A private Kubernetes sandbox has
one online GPU pool, an asynchronous queue, an object-store-backed model cache,
a serving deployment, KEDA, and a telemetry collector. Prerequisites are a
reviewed Linux GPU cluster, administrator-approved device integration, level 8
artifacts, and two synthetic tenants. If physical GPUs are unavailable, use a
stub server for controller logic and mark GPU, MIG, and performance gates pending.

Exact Kubernetes APIs: `apps/v1 Deployment`, `v1 Service`,
`v1 PersistentVolumeClaim`, `networking.k8s.io/v1 NetworkPolicy`,
`rbac.authorization.k8s.io/v1 Role` and `RoleBinding`,
`autoscaling/v2 HorizontalPodAutoscaler`, and KEDA's
`keda.sh/v1alpha1 ScaledObject`. A reviewed NVIDIA-specific pod fragment is:

```yaml
resources: {requests: {cpu: "2", memory: 4Gi}, limits: {cpu: "4", memory: 8Gi, nvidia.com/gpu: 1}}
```

The fragment is not a complete deployment. Choose CPU/RAM limits from measurements,
add the correct toleration and node affinity, mount an immutable approved model,
and provide startup/readiness probes. Kubernetes copies the GPU limit into the
request when the request is omitted; explicitly setting both requires equality.
KEDA's trigger should measure actionable queue or service pressure, not token
throughput alone. Preserve one warm replica for the interactive track; compare
scale-to-zero only for a workload that accepts its cold-start delay.

Burst queued tasks, remove access to the model store in the lab, and evict a
single approved test pod. Record scheduler delay, image loading, weight loading,
warmup, and first usable token separately. Attempt tenant B access to tenant A's
retrieval fixture and cached answer; both must fail. Exercise a simulated regional
restore from signed artifacts into a separate namespace or cluster.

Expected output, unexecuted: A startup waterfall, bounded queue, isolation evidence,
and recovery timing. Observe an unsatisfied taint, missing device allocation,
readiness before weights load, cache stampede, and cold failover. Production
equivalent: A platform acceptance test, not a claim that pod readiness proves
service readiness. Pass when faults are attributed correctly, isolation holds,
and recovery meets the declared educational target or is explicitly rejected.

## Level 10 principal architect

### Module 26 Enterprise architecture and portfolio decisions

Principal-level design starts with business outcomes, risk appetite, demand,
and constraints before selecting a model or platform. Translate those inputs
into workload classes and explicit decision boundaries: buy versus build,
shared versus isolated serving, adaptation versus retrieval, and managed versus
self-operated infrastructure. Use a reference architecture to standardize
identity, evidence, artifact flow, and telemetry while allowing runtime adapters
where hardware or regulation differs. Compare portfolio reuse with coupling and
shared failure domains. A standard model gateway can simplify policy but become
a central outage path or hide provider-specific behavior. Quantify the cost of
that abstraction and define escape hatches. Defend choices using measured
workload envelopes and rejected alternatives, including simpler non-LLM solutions.
Architecture quality is demonstrated by traceable decisions and controlled
change, not by the number of boxes in a diagram.

* Prerequisites: Levels 1-9
* Suggested hours: 18
* Deliverable: Enterprise reference architecture and five architecture decision records
* Gate: Trace every major component to a requirement, owner, failure mode, and measurable acceptance criterion

### Module 27 Architecture assurance and organizational leadership

Architecture assurance asks whether the evidence is adequate for the consequence
of failure. Establish decision rights across product, data science, platform,
security, legal, finance, and operations without making every change depend on
one committee. Define minimum release evidence, exception expiry, ownership,
and escalation paths. Review uncertainty explicitly: model behavior, traffic
forecasts, hardware supply, and evolving runtime support have different risk
controls. Rehearse migration, incident containment, and disaster recovery with
teams that own the dependencies. Use service-level and cost commitments that
can actually be measured. Mentor peers by asking for counterexamples and
alternative explanations rather than rewarding agreement with the reference
design. A principal architect must also retire unnecessary complexity and stop
an unjustified deployment. Document which decisions are reversible experiments
and which create long-lived regulatory, data, or infrastructure commitments.

* Prerequisites: Module 26
* Suggested hours: 18
* Deliverable: Assurance checklist, ownership matrix, exception policy, and review agenda
* Gate: An independent reviewer can identify the approver, evidence, and reversal path for each high-impact decision

### Module 28 Capstone design and evidence defense

Integrate the lifecycle into one bounded enterprise service rather than building
a miniature foundation-model company. Choose a document assistant or supervised
operations copilot with synthetic tenants, an approved small model, one adaptation
experiment, one retrieval path, and sandboxed tools. Reuse earlier evidence but
check compatibility across the assembled release. Present model, application,
and agent evaluations separately; reconcile memory, capacity, latency, and cost;
then rehearse a failed candidate and a recovery scenario. The capstone includes
a written design and an oral defense in which a reviewer changes a constraint.
Explain what changes, what remains invariant, and what must be remeasured.
Success is an honest, reproducible decision package, including rejected
features and unresolved risks. It is not a production certification, and a
well-supported no-go decision can satisfy the learning objective.

* Prerequisites: Modules 1-27 and resolved or clearly marked hardware evidence gaps
* Suggested hours: 28
* Deliverable: Capstone package, demonstration record, and architecture defense
* Gate: Pass the capstone rubric below with no undisclosed assumptions or unexecuted results presented as measurements

### Lab 10 Architecture review under a changed constraint

Objective: Defend an enterprise service using evidence, then revise it when the
operating envelope changes. Architecture: Reuse the platform diagram below with
one deployment cell, one standby cell, two tenants, a release registry, and
separate evaluation and serving identities. Prerequisites are the nine earlier
labs and an independent reviewer if available. A solo tabletop is useful but
must not be labeled an independent assurance review.

API contract anchors are the level 7 inference APIs, level 9 Kubernetes APIs,
OTLP telemetry, and an immutable OCI image manifest reference. The course-owned
release contract below is a design sketch, not an industry-standard schema:

```json
{
	"release_id": "capstone-candidate-02",
	"model_digest": "required-sha256",
	"runtime_image_digest": "required-sha256",
	"tokenizer_digest": "required-sha256",
	"prompt_digest": "required-sha256",
	"retrieval_snapshot": "required-immutable-id",
	"tool_policy_digest": "required-sha256",
	"evaluation_digest": "required-sha256",
	"approval_state": "pending"
}
```

Replace placeholders with genuine evidence only during later implementation.
Demonstrate one clean release, one rejected release, and a rollback that restores
the complete bundle. The reviewer then introduces one constraint: no external
network, doubled context length, regional capacity loss, or a new tenant requiring
hard isolation. Produce a revised memory/capacity estimate, threat boundary,
dependency list, and decision record before changing any running environment.

Expected output, unexecuted: A defensible go/no-go decision, revised architecture,
and evidence-gap register. Observe stale cost assumptions, missing offline
dependencies, incompatible retrieval rollback, and insufficient warm reserve.
Production equivalent: A principal architect's investment and release review.
Pass when the revised plan remains internally consistent, identifies new tests,
and assigns owners without pretending that a tabletop proves runtime behavior.

## Engineering calculations to reuse across levels

### Effective batch, steps, and loss normalization

For data-parallel degree D, microbatch size b per data-parallel replica, and
accumulation factor A, the effective example batch is:

$$B_{effective}=bAD$$

Tensor-parallel ranks cooperating on the same examples do not multiply this
batch again. For 10,240 examples, b=4, A=8, and D=2, the effective batch is 64
examples and a complete epoch has 160 optimizer updates, assuming no dropped
or padded examples and full accumulation groups. Three epochs have 480 updates.
If each example contains 512 nonpadding training tokens, that is 32,768 tokens
per update; variable-length records invalidate that fixed conversion.

Loss normalization must match the objective. Averaging each microbatch's mean
equally is correct only when their relevant example/token counts are equal.
For variable-length language modeling, aggregate summed token loss divided by
the total number of valid target tokens, with the distributed reduction's
scaling accounted for. Track examples seen, valid tokens seen, successful
optimizer steps, skipped steps, and scheduler steps separately. This explains
why two runs labeled three epochs can follow different optimization trajectories.

### Weight and training-state memory

Use decimal parameter counts: 7B means 7,000,000,000 parameters. GB is 10^9 bytes;
GiB is 2^30 bytes. For a uniform b-bit representation, the ideal weight payload is:

$$M_{weights}=P\frac{b}{8}$$

| Parameters | FP32 weights GB | BF16/FP16 weights GB | INT8 payload GB | INT4 payload GB | BF16/FP16 weights GiB |
| --- | --- | --- | --- | --- | --- |
| 7B | 28 | 14 | 7 | 3.5 | 13.04 |
| 13B | 52 | 26 | 13 | 6.5 | 24.21 |
| 70B | 280 | 140 | 70 | 35 | 130.39 |

INT4 and INT8 values are ideal packed payloads, not device-fit promises. Add
scales, zero points where used, grouping metadata, padding/alignment, unquantized
layers, adapters, and runtime conversion buffers. Some kernels unpack or retain
additional representations. FP16 and BF16 both occupy two bytes but do not have
the same numerical range. A model's advertised parameter count is rounded, so
use its actual tensor inventory for final planning.

Persistent full-training tensor state can be written as:

$$M_{state}=P(b_w+b_g+b_m+b_v+b_{master})$$

Here each b is bytes per parameter for resident weights, gradients, first moment,
second moment, and an optional extra master copy. This is a ledger, not an
optimizer law. Three explicit examples illustrate the difference:

* FP32 parameters and gradients with two FP32 Adam moments: 4+4+4+4+0=16 bytes per parameter
* Low-precision resident weights/gradients with two FP32 moments and an additional FP32 master copy: 2+2+4+4+4=16 bytes per parameter
* Low-precision resident weights, FP32 gradients and moments, and an additional FP32 master copy: 2+4+4+4+4=18 bytes per parameter

| Parameters | Example 16-byte state GB | Example 18-byte state GB | 16-byte state GiB | 18-byte state GiB |
| --- | --- | --- | --- | --- |
| 7B | 112 | 126 | 104.31 | 117.35 |
| 13B | 208 | 234 | 193.72 | 217.93 |
| 70B | 1,120 | 1,260 | 1,043.08 | 1,173.47 |

The official Hugging Face memory guide describes an 18-byte arrangement; the
PyTorch AMP example creates model parameters in default precision and autocasts
operations. Neither supports saying all Adam training always uses 16 bytes or
all mixed-precision training always has two persistent weight copies. State
dtypes depend on optimizer implementation, sharding, precision policy, and
configuration. AMSGrad can add another state; quantized optimizers can use less;
SGD without momentum has fewer persistent tensors.

Add activations, temporary workspaces, communication buffers, allocator
fragmentation/reservation, framework context, and checkpoint staging to derive
peak training memory. FSDP/ZeRO changes per-rank residency but introduces gathers
and other transients; do not divide every memory category by GPU count. For LoRA,
the frozen base remains resident, while gradients and optimizer states primarily
scale with the trainable adapter parameter count, plus any explicitly unfrozen
parameters. For a linear map of dimensions d_in by d_out, rank-r LoRA adds
r(d_in+d_out) parameters. At 4,096 by 4,096 with r=8, that is 65,536 rather than
16,777,216 full-matrix parameters. Activations remain a separate budget.

### KV cache for a concrete GQA decoder

For ordinary full-attention decoder layers with uniformly retained KV state:

$$M_{KV}=2L H_{kv} d_h s\sum_{i=1}^{C}T_i$$

The factor 2 counts keys and values, L is layer count, H_kv is KV heads,
d_h is head dimension, s is bytes per element, and T_i is retained tokens for
sequence i. Query-head count is not a substitute for KV-head count under GQA.
For L=32, H_kv=8, d_h=128, and BF16 s=2:

$$M_{KV/token}=2\times32\times8\times128\times2=131072\ bytes=128\ KiB$$

Define 128K as 131,072 retained tokens. One sequence then consumes exactly
17,179,869,184 bytes, or 16 GiB, of ideal KV payload. If 128K means 128,000
tokens instead, the result is 16.777216 GB or 15.625 GiB. State the convention.
Four independent fully occupied 131,072-token sequences require 64 GiB of KV
payload before weights and overhead. An 8,192-token sequence uses 1 GiB.

A deployment admitting a 128K prompt must still reserve output tokens within its
supported total length. Prefix sharing may reduce physical storage when exact
prefixes and policy permit; paging adds allocation granularity, not free context.
Sliding-window/hybrid attention, compressed latent caches, quantized caches,
offloading, and eviction require model-specific formulas. Tensor parallelism
can shard KV heads in supported layouts, but replication occurs in some
head-count/parallel-degree combinations. Always examine per-rank allocation.

The device budget is weights plus KV plus runtime workspace plus other resident
state and safety headroom. This is why a 7B weight file fitting a GPU does not
prove that four long-context users fit it. The vLLM startup KV-token capacity
estimate is useful evidence, but it remains a memory estimate, not an SLO
throughput guarantee under arbitrary traffic.

### Compute, bandwidth, and collective traffic

A first-order dense-transformer training estimate is approximately 6PN FLOPs
for P parameters and N training tokens, under common forward/backward counting
assumptions and when parameter matmuls dominate. It omits important attention,
embedding, recomputation, communication, and optimizer costs. It is not a
reliable long-context or MoE procurement model without refinement. With achieved
aggregate useful throughput F_eff, time is approximately 6PN/F_eff. Do not use
peak advertised tensor FLOPs as F_eff without an efficiency assumption and a
matched precision/sparsity convention.

For an operation doing F FLOPs and moving Q bytes, an idealized roofline lower
bound is max(F/F_peak, Q/BW). Launch overhead, synchronization, communication,
and contention make actual time longer. HBM bandwidth is not PCIe bandwidth;
NVLink/NVSwitch connectivity does not automatically imply an equally fast
inter-node path. For a ring all-reduce of S bytes across D ranks, the idealized
per-rank transferred volume is about 2(D-1)S/D, plus latency effects. NCCL may
select another algorithm or topology. Use this to explain trends, not to predict
an exact benchmark without measuring the actual collective.

### Concurrency and Little's Law

For a stable system with consistently defined boundaries:

$$\bar{L}=\lambda\bar{W}$$

At 20 requests/second and mean end-to-end residence time four seconds, mean
requests in the system are 80. If mean queue time is one second and mean active
service time three seconds, average queued requests are 20 and active requests
60. The engine's active batch is not necessarily 80. Do not mix a gateway
arrival rate with an engine-only latency or substitute p95 latency for a mean.

With mean output 400 tokens/request, this arrival rate requires 8,000 output
tokens/second, plus prompt processing. A measured replica rate must be obtained
at the same prompt/output distribution and latency objective. A lower bound on
replica count comes from both throughput and concurrent memory occupancy, then
increases for bursts, failure reserve, cold starts, and tenant fairness. Average
stability does not bound tail latency; queued work can diverge when arrivals
exceed sustained service. Agent tasks further multiply requests through retries
and tool/model loops, so forecast both user-task arrivals and inference calls.

### Explicitly fictional illustrative cost model

These are invented prices and performance numbers for arithmetic practice, not
quotes, measured results, or claims about any provider or GPU SKU. Assume four
GPUs at $2.50 per GPU-hour, always allocated for a 30-day month of 720 hours.
Add $1,800 monthly for invented platform/storage/operations allocation. Assume
the fleet delivers 1,000 output tokens/second while active and is active at that
rate for 40 percent of the month. Ignore variable charges only for this exercise.

$$Cost=4\times2.50\times720+1800=\$9000$$

$$Tokens=1000\times0.40\times720\times3600=1{,}036{,}800{,}000$$

The illustrative allocated cost is $8.68 per million output tokens. If only
90 percent of those output tokens are attributed to accepted successful tasks
under the exercise's accounting rule, useful output is 933.12 million tokens,
and the cost becomes $9.65 per million useful output tokens. This convention
must not be silently substituted for cost per successful task. At 20 percent
activity with unchanged fixed cost, raw output-token cost doubles to $17.36 per
million. Training cost, idle failover capacity, egress, prompt processing,
evaluation, licensing, power, staffing, and failed requests need explicit
inclusion in a real total-cost model; several are only hidden in the invented
allocation here. Token-level savings can still increase cost per useful task
if the cheaper path creates retries or low-quality answers.

## Serving alternatives and lifecycle decisions

| Alternative | Appropriate role | Important limitations | Curriculum treatment |
| --- | --- | --- | --- |
| PyTorch plus Transformers | Transparent reference execution and small experiments | Not automatically a complete production scheduler, admission controller, or fleet manager | Numerical truth path and adaptation baseline |
| vLLM | LLM-focused execution, continuous scheduling, paged KV, compatible APIs, parallel serving | Model/hardware/feature combinations must be qualified; current kernel details differ from historical PagedAttention explanation | Default measured LLM-serving lab |
| Triton Inference Server | Multi-backend model serving, ensembles, HTTP/gRPC, dynamic and sequence scheduling | Generic dynamic batching is not identical to LLM token-level scheduling; backend compatibility determines LLM behavior | Compare for mixed ML/LLM estates |
| TGI | Existing Hugging Face text-generation deployments | Official docs explicitly say maintenance mode, accepting minor fixes/docs/lightweight maintenance | Teach operation and migration; do not choose as the default new investment |
| TensorRT-LLM | NVIDIA-focused optimized LLM runtime and serving | Hardware/model/feature support and version coupling require validation; current docs remove the old TensorRT execution backend | Benchmark as a specialized alternative, not assume superiority |
| ONNX plus ONNX Runtime | Portable graph artifacts and execution-provider-based inference | Graph export/opset/dynamic-shape support varies; an InferenceSession is not an entire LLM service | Useful for classifiers, encoders, and qualified generation paths |

Triton Inference Server is distinct from the Triton GPU kernel language. Triton
can host specialized backends; compare the entire deployed stack rather than
pretending a model server and an execution engine are mutually exclusive.
Its generic dynamic batcher combines compatible stateless requests. Iterative
sequences support stepwise scheduling for compatible backends, but the retrieved
documentation labels that feature provisional. Confirm the exact backend/version
when teaching continuous batching through Triton.

The TGI documentation was retrieved directly and explicitly directs future use
toward engines including vLLM and SGLang, with local alternatives such as llama.cpp
or MLX. Maintenance mode does not mean every installation immediately fails or
that a specific security support end date exists. No such date was established.
Inventory models, templates, stop behavior, log probabilities, streaming,
quantization, metrics, and performance before migration. Compare candidates with
the same release bundle and traffic; API resemblance alone is insufficient.

The retrieved TensorRT-LLM migration page, updated September 4, 2026 and generated
from commit c295dd9, says PyTorch is now its sole execution backend. It says the
old `trtllm-build`/conversion path is removed and Hugging Face checkpoints load
directly. Therefore a current course must not mandate an engine-build step for
every TensorRT-LLM deployment. Older pinned releases may retain that workflow;
label historical examples and match documentation to the installed version.
This is a documentation observation, not a local compatibility test.

Choose the first runtime through an acceptance matrix: supported architecture,
precision, context, adapters, structured outputs, streaming cancellation,
hardware, startup behavior, memory, goodput, security controls, and upgrade
process. Then test a second candidate only where a decision could change.
Do not run six full stacks merely to populate a technology checklist. Optional
SGLang or local-engine comparisons can follow the core course, but their
compatibility and lifecycle were not investigated independently here.

## Enterprise reference architecture

### Proposed cloud-neutral topology

```text
OFFLINE CONTROL AND EVIDENCE PLANE
Sources --> [1 Intake / rights / privacy] --> [2 Versioned corpora]
[2] --> [3 Training / adaptation] --> [5 Candidate artifact store]
[2] --> [4 Retrieval snapshots]
[CI builders / SBOM] --> [5]
[5] --> [6 Independent evaluation / humans] --> [7 Release registry]
[7] --> [8 GitOps / admission / deployment] --> signed serving bundle

ONLINE DATA PLANE
Clients --> [9 Identity / gateway / admission] --> [10 Application / agent]
[10] --> [11 ACL retrieval] --> [4 Retrieval snapshot]
[10] --> [12 Model router] --> [14 Serving cell A / GPU replicas / KV]
[12] --> [Exact response cache] --> cache miss to [14]
[12] --> [Async queue] --> [14]
[10] --> [13 Tool policy broker] --> [Sandbox / approved APIs]
[Model cache / immutable weights] --> [14]
[9 Gateway failover] --> [15 Independent cell B / warm reserve]
[8 Approved bundle] --> [14] and [15]

FEEDBACK AND OBSERVABILITY PLANE
All components --> [16 OTel / metrics / audit / quality joins]
[16] --> [17 Incident and feedback triage]
[17] --> reviewed data to [1], never directly to training
```

### Interaction contracts and ownership

1. Intake admits only permitted sources, records rights and provenance, and
	quarantines suspicious or sensitive records. The data owner authorizes use;
	ingestion does not automatically grant training rights. Identity, retention,
	deletion, and export constraints travel with the data.
2. Versioned storage records immutable manifests and transformation identities.
	Training and retrieval may derive different products from the same source.
	Split assignment precedes transformations that could leak family information.
	Mutable external URLs are not enough to reconstruct an experiment.
3. Training reads an approved corpus and writes candidate artifacts plus state
	and experiment evidence. Its workload identity cannot approve a production
	release. Distributed workers remain on a trusted private fabric with
	controlled access to checkpoints and collective rendezvous endpoints.
4. Retrieval snapshots include document ACLs, embedding model identity, chunking,
	indexes, and freshness metadata. Application retrieval checks the caller's
	authorization before context is assembled. A snapshot rollback must remain
	compatible with current deletion and access-control requirements.
5. Artifact storage preserves weights, adapters, tokenizer/template/config,
	quantization metadata, and runtime references. CI produces reviewed images
	and software bills of materials. Signatures establish identity and provenance,
	not behavioral safety; the evaluator still tests the resulting candidate.
6. Independent evaluation consumes candidate bundles and protected held-out
	tasks. It emits raw task evidence, statistics, evaluator identity, and human
	review outcomes. Evaluation errors produce non-pass states. Training jobs
	must not gain access to private benchmark answers through shared credentials.
7. The registry binds immutable artifacts to approvals and supported workload
	envelopes. An approval names the evidence, owner, and expiry/review conditions.
	The serving path resolves a release bundle, not a floating latest-model label.
8. Deployment controllers reconcile approved state and admission checks enforce
	artifact and policy requirements. Rollout controllers coordinate stable and
	candidate routing with verified integrations. GitOps reports configuration
	convergence; quality readiness comes from separate release and runtime checks.
9. The gateway authenticates clients, establishes tenant identity, validates
	limits, and enforces deadlines and quotas before expensive work. It propagates
	trace context and cancellation. A central gateway needs its own availability
	design; avoid making all regions depend on one unprotected instance.
10. The application constructs prompts and coordinates retrieval, model calls,
	 and tools under a bounded execution budget. It preserves release identity
	 throughout a session or explicitly manages transitions. Agent state records
	 observed tool outcomes, not merely the model's claim that an action succeeded.
11. Retrieval returns authorized evidence with source identities. The application
	 distinguishes source data from executable instructions. Index freshness,
	 recall, permissions, and answer grounding have separate monitors and owners.
12. The router selects an approved model based on workload and tenant policy,
	 not solely lowest cost. Exact response caching, semantic caching, and prefix
	 KV reuse are different mechanisms with different correctness guarantees.
	 Cache keys include tenant, release, authorization context, and relevant
	 corpus/template identity. Async queues preserve deadlines and idempotency.
13. The tool broker authorizes each action outside the model and mediates access
	 to sandboxed or approved business APIs. High-impact actions need explicit
	 approvals and audit. Shadow requests cannot execute business side effects;
	 generated arguments remain untrusted until validated and authorized.
14. A serving cell admits bounded work into replicas with known model and cache
	 budgets. Local weight caches reduce startup traffic; they verify digests and
	 avoid simultaneous unbounded downloads. GPU pools separate training bursts
	 from interactive SLOs. A TP/PP group is one coordinated replica for failure
	 and scaling purposes, not several independently useful HTTP pods.
15. A standby or second active cell loads approved compatible artifacts and has
	 reserved capacity. Failover handles DNS/gateway state, identity, retrieval,
	 queues, and audit, not just weights. In-flight KV typically need not be
	 replicated; define restart/resume behavior at the application contract.
16. Telemetry collects bounded metadata with explicit sampling and retention.
	 Quality joins correlate delayed outcomes with releases while limiting access
	 to content. GPU utilization, queue pressure, first-token latency, task quality,
	 and privacy violations remain distinguishable signals.
17. Incident and feedback triage separates containment from learning. Reviewed
	 evidence may produce a new corpus or regression test only after consent,
	 privacy, and split checks. No arrow from production feedback directly updates
	 model weights. Product, data, platform, and security owners decide the action.

Cloud, on-premises, and air-gapped deployments implement the same contracts
through different identity, object storage, registries, GPU pools, and network
adapters. No Azure-specific design or deployment is proposed here. Such adapters
require a separate cloud-specific best-practice and documentation pass. An
air-gapped plan must mirror weights, tokenizers, packages, images, trust roots,
licenses, documentation assets, and recovery dependencies before disconnection.
It must also plan controlled updates and evidence export rather than assuming
that removing internet access solves supply-chain risk.

## Learner-first case prompts

Do not read these as solved architecture patterns. For each case, first list
unknowns, write a testable hypothesis, identify the smallest discriminating
experiment, and state the evidence that would reverse your decision. No answers
are supplied.

1. A domain adapter reduces training loss by 35 percent but user task success
	does not improve. What would you inspect before acquiring more data or
	increasing rank? Define a comparison that separates objective, data, and
	application effects.
2. A 7B model's weights fit comfortably on a GPU, yet four long-context sessions
	trigger out-of-memory errors. What measurements and dimensions are missing
	from the team's fit calculation? Propose a bounded admission experiment.
3. A benchmark gain is two percentage points, but candidate answers are much
	longer and the judge prefers the first answer shown. How would you decide
	whether the gain is meaningful without tuning on the final holdout?
4. Moving from one node to two doubles GPU count and lowers throughput. Which
	hypotheses would distinguish tensor shape, fabric, collective participation,
	and data-loading problems? Specify the evidence needed before redesigning.
5. An existing TGI estate serves five model families with undocumented stopping
	behavior. How would you decide whether and how to migrate now that upstream
	documents maintenance mode? Define equivalence and rollback requirements.
6. KEDA creates new pods during a burst, but users still wait minutes for the
	first token. What time boundaries would you instrument, and which controls
	are owned by workload scaling versus node provisioning versus model loading?
7. Two tenants share a semantic response cache. An answer is factually correct
	but contains a document reference belonging to the other tenant. What does
	this reveal about the release's acceptance criteria and isolation design?
8. GRPO reward climbs steadily while a human review finds repetitive,
	low-information responses. How would you distinguish reward design,
	generation policy, implementation defaults, and genuine task improvement?
9. Finance requests a 40 percent cost reduction and operations requires regional
	failover without reduced service. Which demand, quality, staffing, and reserve
	assumptions must be tested before promising both outcomes?
10. A regulated customer requires offline operation within six weeks. Your
	 current service downloads tokenizer assets and documentation at startup and
	 uses an external judge. What would the architecture review require before
	 approving the proposed air-gapped deployment?

## Capstone request and acceptance rubric

Prepare a decision package for a two-tenant enterprise knowledge and operations
assistant using only synthetic or explicitly permitted documents and sandboxed
tools. Select one narrow business task with measurable success, one retrieval
path, one model adaptation comparison, and one candidate serving stack. Include
a non-LLM or prompt-only baseline. Keep this an engineering demonstration, not
an autonomous production operations agent.

The request is to submit a requirements envelope, data/model cards, lineage
manifest, architecture diagram, five decision records, paired evaluation,
capacity and memory workbook, load-test record, privacy/isolation checks,
release/rollback evidence, DR tabletop, and an unresolved-risk register. Separate
observed measurements from estimates and expected results in every artifact.
Identify which earlier lab evidence is reused and which must be rerun because
the assembled release changes a dependency.

| Criterion | Points | Observable requirement |
| --- | --- | --- |
| Problem and baseline | 10 | Explicit task, users, constraints, simpler baseline, and no-go conditions |
| Data and adaptation | 15 | Permitted provenance, split integrity, adaptation comparison, and retention checks |
| Evaluation | 20 | Model/application/agent separation, raw paired evidence, uncertainty, and mandatory safety gates |
| Runtime and capacity | 15 | Reconciled memory ledger, matched load matrix, SLO-qualified goodput, and reserve |
| Operations and recovery | 15 | Immutable release, telemetry correlation, rejected candidate, rollback, and DR limits |
| Security and privacy | 15 | Tenant tests, tool authorization, artifact verification, and content-retention boundaries |
| Decision defense | 10 | Rejected alternatives, accountable owners, constraint-change response, and honest gaps |

An educational pass is at least 80/100 plus all mandatory integrity requirements:
no unauthorized data, no hidden test leakage, no unexecuted claim represented as
measurement, no cross-tenant disclosure in fixtures, and no production side
effects. A missing physical distributed test can remain a clearly scoped gap;
it prevents claims of validated multi-GPU performance rather than invalidating
all architecture work. A no-go decision can pass if evidence supports it.

After the defense, ask for a targeted second iteration, not another broad
curriculum: for example, improve long-context goodput under a fixed quality
margin, reproduce a two-rank scaling failure, or qualify a runtime migration.
Repeated focused iterations are how course competence becomes practical depth.

## Primary-source verification register

Sources below were fetched and their relevant content inspected in this session
on the requested research date, 2026-09-13. They are free primary project or
author sources, including vendor-authored documentation where it defines that
vendor's technology. Documentation verification is not execution verification,
a package-version lock, or an independent performance benchmark. Avoid importing
vendor throughput claims into capacity planning without reproducing the workload.

| ID | Primary source | Claim supported and verification limit |
| --- | --- | --- |
| S01 | [PyTorch AdamW](https://docs.pytorch.org/docs/2.14/generated/torch.optim.AdamW.html) | Decoupled weight decay, optimizer state APIs, and additional foreach peak memory; stable alias redirected to this version |
| S02 | [PyTorch AMP examples](https://docs.pytorch.org/docs/2.14/notes/amp_examples.html) | Autocast/GradScaler roles, effective-batch accumulation, unscale-before-clip, and step skipping; examples inspected, not executed |
| S03 | [Hugging Face GPU memory anatomy](https://huggingface.co/docs/transformers/model_memory_anatomy) | Weights, moments, gradients, activations, and temporary tensors; its example precision arrangement is not universal |
| S04 | [Transformers Llama](https://huggingface.co/docs/transformers/en/model_doc/llama) | Configuration fields, GQA head distinction, RMSNorm/RoPE/SwiGLU, logits and cache contracts; model-specific rather than every transformer |
| S05 | [Transformers chat templates](https://huggingface.co/docs/transformers/en/chat_templating) | Training generation-prompt setting and duplicate special-token warning; actual model templates still require inspection |
| S06 | [Compute-optimal training paper](https://arxiv.org/abs/2203.15556) | Author abstract supports jointly scaling model size and training tokens under a compute budget; not a universal deployment-cost optimum |
| S07 | [PyTorch tensor parallel tutorial](https://docs.pytorch.org/tutorials/intermediate/TP_tutorial.html) | Tensor/sequence parallel distinctions, DTensor, device meshes, FSDP composition, and fast-link motivation; snippets require version-matched correction and validation |
| S08 | [NCCL collectives](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/usage/collectives.html) | All-reduce/all-gather/reduce-scatter/all-to-all semantics and compatible rank participation; actual algorithm/topology is runtime-selected |
| S09 | [TRL DPO trainer](https://huggingface.co/docs/trl/en/dpo_trainer) | Preference-pair format, standard reference-relative objective, and no explicit reward-model requirement; evolving options not treated as fixed defaults |
| S10 | [TRL GRPO trainer](https://huggingface.co/docs/trl/en/grpo_trainer) | Group completion generation, rewards, relative advantages, and implementation variants; current defaults differ from original-paper assumptions |
| S11 | [PEFT quantization guide](https://huggingface.co/docs/peft/en/developer_guides/quantization) | QLoRA workflow, BitsAndBytesConfig, k-bit preparation, LoRA targeting, and backend merge caveats; hardware compatibility not tested |
| S12 | [PEFT IA3](https://huggingface.co/docs/peft/en/conceptual_guides/ia3) | Learned activation-scaling vectors and frozen base weights; comparative quality claims remain task-dependent |
| S13 | [SciPy bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html) | Paired index resampling, BCa intervals, RNG API, and degenerate-data warning; cluster sampling requires an appropriate design |
| S14 | [vLLM parallelism and scaling](https://docs.vllm.ai/en/stable/serving/parallelism_scaling/) | TP/PP options, KV-token capacity logging, topology concerns, and private-network warning; no local distributed benchmark |
| S15 | [vLLM online serving](https://docs.vllm.ai/en/stable/serving/online_serving/) | Completion/chat/health/metrics endpoints, required chat templates, and development/admin endpoint warnings |
| S16 | [vLLM Paged Attention historical design](https://docs.vllm.ai/en/latest/design/paged_attention/) | Blocked KV storage and explicit warning that the historical kernel description no longer matches current code; conceptual reference only |
| S17 | [TGI official documentation](https://huggingface.co/docs/text-generation-inference/en/index) | Explicit maintenance-mode notice and recommended successor engines; no support end date established |
| S18 | [Triton batchers](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/batcher.html) | Stateless dynamic batching versus stateful/iterative scheduling; iterative sequences documented as provisional |
| S19 | [TensorRT-LLM documentation](https://nvidia.github.io/TensorRT-LLM/) | Current API, serving, KV, parallelism, and model-support documentation entry points; no throughput ranking inferred |
| S20 | [TensorRT-LLM backend migration](https://nvidia.github.io/TensorRT-LLM/legacy/tensorrt-backend-removal.html) | Current docs state TensorRT execution backend and engine-build workflow removed; September 4, 2026, commit c295dd9 |
| S21 | [ONNX Runtime Python guide](https://onnxruntime.ai/docs/get-started/with-python.html) | ONNX export/checking and InferenceSession/run APIs; generic inference does not imply full generative serving support |
| S22 | [Kubernetes GPU scheduling](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/) | Drivers/device plugins, extended GPU resources, equal request/limit rule, and labels/affinity |
| S23 | [NVIDIA GPU sharing](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html) | MIG memory/fault isolation versus time-slicing limitations; supported hardware and operator version must be selected later |
| S24 | [KEDA deployment scaling v2.18](https://keda.sh/docs/2.18/concepts/scaling-deployments/) | KEDA activation versus HPA scaling and long-running termination concerns; page marks v2.18 nonlatest and points to v2.20 |
| S25 | [OpenTelemetry GenAI move notice](https://opentelemetry.io/docs/specs/semconv/gen-ai/) | Old location is no longer maintained and points to a separate repository |
| S26 | [OpenTelemetry GenAI repository](https://github.com/open-telemetry/semantic-conventions-genai) | New home for conventions; retrieved README has schema URL TODO and no published releases, so no stable schema guarantee is claimed |
| S27 | [Argo Rollouts traffic management](https://argoproj.github.io/argo-rollouts/features/traffic-management/) | Native Service limitations, routing integrations, stable/canary separation, and mirroring; support differs by router |

Evidence is applied as follows: S01-S03 ground level 2 and training-state
calculations; S04-S05 ground level 3 and the GQA dimensions; S06-S10 ground
level 4; S11-S12 ground level 5; S13 grounds statistical APIs in level 6;
S14-S21 ground level 7 and serving choices; S25-S26 ground level 8's schema
caveat; S22-S24 and S27 ground platform scaling and controlled delivery.
Educational hours, acceptance margins, enterprise component boundaries, and
the cost scenario are recommendations or derived examples, not source claims.

Several fetched pages contain fast-moving defaults, legacy examples, or broad
marketing statements. The curriculum deliberately does not copy those as
universal facts. For example, a PyTorch tutorial may show abbreviated mesh
setup while later indexing named dimensions; an implementation must supply
matching mesh names rather than blindly paste the excerpt. Likewise, a training
guide's memory layout does not specify every optimizer's runtime tensor dtype.
Read API contracts together with measured state in the selected release.

Two original vLLM URLs were moved or failed extraction. The old distributed
serving URL yielded no useful content; parallelism_scaling was fetched instead.
The compatible-server URL redirected to online_serving, whose content was then
retrieved. PyTorch redirects were followed to explicit 2.14 pages. These
recoveries are not counted as independent supporting sources.

## Coverage and evidence boundaries

The requested topic families map to modules without adding extra levels:

* Optimizers, learning rate, epochs, updates, batch/accumulation, and mixed precision: 3-4
* Transformer QKV shapes, masking, RoPE, normalization, FFN, logits, and generation: 5-7
* Pretraining, continuation, SFT, RLHF, DPO, GRPO, reward, synthetic mixtures, curricula, and scaling: 8-10
* Full FT, LoRA, QLoRA, bottleneck adapters, prefix/prompt tuning, IA3, and quantization: 11-13
* Model/application/agent, human/judge/pairwise statistics, leakage/contamination, drift, safety, long context, and tools: 14-16
* Registries, packaging, vLLM/Triton/TGI/TensorRT-LLM/ONNX, online/batch/async/streaming: 17-19
* Prefill/decode, KV, continuous batching, paging, speculation, tensor parallelism, GPU HBM/FLOPs/bandwidth/fabrics: 9 and 18
* DP/TP/PP/SP/CP/EP, MoE, collectives, and InfiniBand: 9, reinforced in 18 and 23
* MLOps/LLMOps/AgentOps, data/prompt/eval versions, release CI/CD and GitOps: 20-22
* End-to-end observability, OTel, quality SLOs, privacy, poisoning, supply chain, isolation, and RBAC: 21 and 24
* Kubernetes plugins/operators, taints, MIG/sharing, KEDA/node autoscaling, storage/caching: 23
* Blue-green, canary, shadow, A/B, champion-challenger, and rollback: 19-20
* Capacity, economics, routing/caching, tenancy, cloud/on-premises/air gap, and DR: 24-27

All ten labs are specifications with expected outputs explicitly marked
unexecuted. No training, model loading, package installation, container build,
cluster operation, or source modification was performed. Numeric results are
analytical calculations, not GPU observations. A later implementation must
verify APIs, model licenses, accelerator availability, resource budgets, and
environment compatibility. The full course is broad lifecycle competence,
not exhaustive mastery of every ML family, multimodal architecture, or research
method. Classical ML baselines and non-transformer inductive biases provide
context; advanced vision, speech, and research specialization are follow-on paths.

ARISE-X remains optional for later evaluation/AgentOps connections. The bootstrap
describes useful contracts and known evidence limitations, but this research
did not reread or execute source to establish new capability claims. Do not
represent ARISE-X as a pretraining or fine-tuning engine on the basis of this
curriculum. YouTube verification, the full first lesson, and PDF production
belong to separate tasks and are not silently claimed complete.

## Remaining questions and recommended next research

No unanswered question blocks the curriculum architecture. Personalization and
implementation need the following inputs; current estimates explicitly assume
small models and 8-10 study hours per week.

* How comfortable are you with matrix calculus, probability, and reading PyTorch training code?
* Is occasional access to one GPU and two Linux GPUs available, and what is the monthly learning budget?
* Is the target role primarily model platform architect, applied AI architect, or training-infrastructure architect?
* Which enterprise workload and jurisdiction should determine the capstone's data and isolation constraints?
* Can a peer review evaluation rubrics and the final architecture defense independently?

Recommended next research not completed in this session:

* [ ] Select a permitted small-model family and pin a tested PyTorch/Transformers/PEFT/TRL/runtime matrix.
* [ ] Verify physical GPU and Linux access; price an approved learning budget using actual quotes rather than the fictional example.
* [ ] Implement and smoke-test the ten labs in a separate approved environment, retaining unexecuted labels until evidence exists.
* [ ] Calibrate statistical sample sizes, safety coverage, and quality thresholds to the selected capstone workload.
* [ ] Recheck TGI lifecycle, TensorRT-LLM workflow, KEDA versions, and GenAI semantic-convention state at course publication.
* [ ] Map the cloud-neutral architecture to a selected cloud or air-gapped estate only when its constraints are known.

Research conclusion: A 28-module, ten-level, measured stage-gated course is
appropriate for this experienced architect. Foundational numerical work stays
brief but mandatory; independent evaluation precedes deployment; operational
skills reconnect to actual learned-system behavior; and the principal-level
capstone tests decision quality rather than technology recall.