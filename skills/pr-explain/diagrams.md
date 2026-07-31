# Diagram recipes (plain ASCII)

All diagrams are plain ASCII inside a fenced ```text block, so they render in
any terminal. No Mermaid, no images. Keep each diagram to the blast radius --
omit unrelated modules. Tag changed nodes with a trailing `*` and note it in a
one-line legend.

## Architecture diagram

Use nested boxes for modules/packages and arrows for relationships. Group a
package's contents inside one box; put the file path on the box header.

```text
codegen/common.py
  register_backend_for_device('cuda') --> CUDACombinedScheduling *

codegen/cuda_combined_scheduling.py
  CUDACombinedScheduling *  (dispatcher)
    |-- choose_node_backend --> [ Triton | CuteDSL | FlyDSL * ]
    +-- codegen_template ------> FlyDSLScheduling *

codegen/flydsl/  (NEW package)
  FlyDSLTemplate * ---------> FlyDSLTemplateKernel *
       |                          (renders source)
       +-- builds ------------> FlyDSLBenchmarkRequest *  [autotune_process.py]
       +-- output_node() -----> FlyDSLTemplateBuffer *    [ir.py]
  FlyDSLScheduling * -------> AsyncCompile.flydsl() *      [async_compile.py]
  runtime_available()        (NEW, not yet called)

  legend: * = changed by this PR
```

Rules:
- One box per module/package; header is the path, body is the symbols.
- `-->` for "calls / produces / routes to"; `|--` `+--` for tree branches.
- Keep node labels to the symbol name plus a 2-3 word role in parens.

## Control flow diagram

A numbered top-to-bottom sequence. Show the participant on the left of the `:`
and the action on the right. Call out changed behavior with a `<-- changed`
marker on its own indented line.

```text
(A) choice generation
  1. select_algorithm : maybe_append_choice()
  2. FlyDSLTemplate   : generate() -> FlyDSLTemplateKernel.render()
  3. FlyDSLTemplate   : build FlyDSLBenchmarkRequest
  4. -> returns FlyDSLTemplateCaller
       caller.output_node() -> FlyDSLTemplateBuffer (ir.py)   <-- new IR node

(B) codegen
  5. CUDACombinedScheduling : is_flydsl_template? -> FlyDSLScheduling
  6. FlyDSLScheduling       : codegen_template() -> define_kernel()
       emits: async_compile.flydsl(name, src)                 <-- new emit
  7. FlyDSLScheduling       : call_kernel() -> wrapper emits kernel(args, stream)

(C) runtime compile
  8. AsyncCompile.flydsl : submit to process pool (reused worker)
  9.                     : _load_kernel_fn -> {name}_main entry point
```

## Data flow diagram

A left-to-right pipe chain with the value named between stages. Use `==>` for the
main data path and label each edge with what flows.

```text
input tensors ==(shape, dtype)==> FlyDSLTemplateKernel.render
      ==(rendered .py source)==> PyCodeCache.write
      ==(module key, path)==> _load_kernel_fn
      ==({name}_main callable)==> wrapper call site *
```

## Guidance

- If a single diagram would exceed ~15 nodes, split by concern rather than
  cramming; a reviewer cannot parse a wall of boxes.
- Align arrows and indentation so columns read cleanly in a monospace terminal.
- Label edges when the *what* flowing matters (types, shapes, states); leave
  them bare when only ordering matters.
- Always wrap diagrams in a ```text fence so nothing gets reflowed.
