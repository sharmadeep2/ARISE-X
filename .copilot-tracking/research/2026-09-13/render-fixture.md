---
title: Learning handbook print validation
description: Independent fixture for math, code pagination, tables, links, and ASCII
ms.date: 2026-09-13
ms.topic: reference
---

## Reading and navigation

SELECTABLE-TEXT-SENTINEL: This independent fixture tests a reusable print pipeline.
It is not the concurrently authored primary handbook. Follow the
[equations section](#equations-and-meaning) and return through the linked contents.

Watch [3Blue1Brown: Gradient descent](https://www.youtube.com/watch?v=IHZwWFHWa-w).
The external video link must remain a clickable PDF annotation, without loading
any remote video or thumbnail while printing.

## Equations and meaning

The prediction is $\hat{y}=wx+b$. A fraction $\frac{1}{2}$ means one half.
Parenthesis-delimited math also works: \(x \in \mathbb{R}^{d}\).

$$
L(w)=\frac{1}{N}\sum_{i=1}^{N}\left(wx_i-y_i\right)^2
$$

This loss is the mean squared difference between the prediction and target.
N is the number of examples, x is the input, y is the target, and w is a weight.

$$
\frac{\partial L}{\partial w}=\frac{2}{N}\sum_{i=1}^{N}(wx_i-y_i)x_i
$$

The partial derivative measures how the loss changes when the weight changes.

$$ \frac{d}{dx}x^2=2x \qquad W\in\mathbb{R}^{d_{out}\times d_{in}} $$

The derivative of x squared is twice x. The matrix W has output-dimension rows
and input-dimension columns. These sentences preserve the meaning if copying
individual mathematical glyphs from a PDF loses their two-dimensional order.

## Configuration and narrow tables

```yaml
training:
    batch_size: 32
    optimizer:
        name: adamw
        learning_rate: 0.0003
    shapes: [batch, sequence, hidden]
    note: "Spacing and indentation must survive print and text selection."
```

| Component | Shape and contract | Reference |
|-----------|--------------------|-----------|
| Embedding | batch_size_by_sequence_length_by_hidden_dimension | [Video](https://www.youtube.com/watch?v=IHZwWFHWa-w) |
| Long identifier | exceptionally_long_identifier_without_any_spaces_must_wrap_inside_the_cell_and_not_clip | <https://www.youtube.com/watch?v=IHZwWFHWa-w&feature=shared&annotation_id=independent_renderer_validation_long_url_wrapping_sample> |
| Loss | Scalar mean, not a per-token vector | See [equations](#equations-and-meaning) |

Long URL outside a table:
<https://www.youtube.com/watch?v=IHZwWFHWa-w&feature=shared&annotation_id=independent_renderer_validation_long_url_wrapping_sample_with_extra_characters_for_the_print_width_check>.

## ASCII architecture

```text
+------------------+      +------------------+      +------------------+
| Input examples   | ---> | Forward + loss   | ---> | Backward + step  |
| x: [batch, dim]  |      | prediction: yhat |      | update weights   |
+------------------+      +------------------+      +------------------+
           |                                                 |
           +--------------- repeat next batch ---------------+
```

Space columns, plus signs, vertical bars, and arrows must remain aligned.

## Page-spanning code

The following unexecuted 120-line code sample must split naturally across pages.
The first line, last line, and all numbered intermediate lines must remain
selectable. A large block must not shrink to fit on one page.

```python
step_001 = 1
step_002 = 2
step_003 = 3
step_004 = 4
step_005 = 5
step_006 = 6
step_007 = 7
step_008 = 8
step_009 = 9
step_010 = 10
step_011 = 11
step_012 = 12
step_013 = 13
step_014 = 14
step_015 = 15
step_016 = 16
step_017 = 17
step_018 = 18
step_019 = 19
step_020 = 20
step_021 = 21
step_022 = 22
step_023 = 23
step_024 = 24
step_025 = 25
step_026 = 26
step_027 = 27
step_028 = 28
step_029 = 29
step_030 = 30
step_031 = 31
step_032 = 32
step_033 = 33
step_034 = 34
step_035 = 35
step_036 = 36
step_037 = 37
step_038 = 38
step_039 = 39
step_040 = 40
step_041 = 41
step_042 = 42
step_043 = 43
step_044 = 44
step_045 = 45
step_046 = 46
step_047 = 47
step_048 = 48
step_049 = 49
step_050 = 50
step_051 = 51
step_052 = 52
step_053 = 53
step_054 = 54
step_055 = 55
step_056 = 56
step_057 = 57
step_058 = 58
step_059 = 59
step_060 = 60
step_061 = 61
step_062 = 62
step_063 = 63
step_064 = 64
step_065 = 65
step_066 = 66
step_067 = 67
step_068 = 68
step_069 = 69
step_070 = 70
step_071 = 71
step_072 = 72
step_073 = 73
step_074 = 74
step_075 = 75
step_076 = 76
step_077 = 77
step_078 = 78
step_079 = 79
step_080 = 80
step_081 = 81
step_082 = 82
step_083 = 83
step_084 = 84
step_085 = 85
step_086 = 86
step_087 = 87
step_088 = 88
step_089 = 89
step_090 = 90
step_091 = 91
step_092 = 92
step_093 = 93
step_094 = 94
step_095 = 95
step_096 = 96
step_097 = 97
step_098 = 98
step_099 = 99
step_100 = 100
step_101 = 101
step_102 = 102
step_103 = 103
step_104 = 104
step_105 = 105
step_106 = 106
step_107 = 107
step_108 = 108
step_109 = 109
step_110 = 110
step_111 = 111
step_112 = 112
step_113 = 113
step_114 = 114
step_115 = 115
step_116 = 116
step_117 = 117
step_118 = 118
step_119 = 119
step_120 = 120
```

## End-of-fixture checks

END-OF-FIXTURE-SENTINEL: Verify this heading stays with this paragraph and that
the page footer contains the page number and total page count. Inline literal
code such as `"$not_math$"` must not be processed as an equation.

```text
    indentation is intentional
        nested indentation remains eight spaces
    long_line = "A deliberately long code line with spaces that must wrap without losing its source indentation or clipping its final sentinel: CODE-WRAP-END"
```