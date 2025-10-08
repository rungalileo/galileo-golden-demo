# Available Galileo Scorers

This document lists all available Galileo metrics/scorers that can be used in experiments.

## Quick Reference

Run this command to see all available scorers at any time:
```bash
python check_available_scorers.py
```

## Commonly Used Scorers

These are the scorers currently configured in the experiments:

### ✅ Currently Used in UI

| Scorer | Description | Required Fields |
|--------|-------------|-----------------|
| `context_adherence` | How well response adheres to provided context | `input`, `output`, `context` |
| `completeness` | Coverage of query requirements | `input`, `output` |
| `correctness` | Accuracy compared to expected output | `input`, `output` (expected) |
| `output_toxicity` | Detection of harmful content in output | `output` |
| `chunk_attribution_utilization` | Whether RAG chunks were used in response | `input`, `output`, chunks |

## All Available Scorers (83 total)

### Response Quality Metrics
- `completeness` - Coverage of requirements
- `completeness_luna` - Luna model version
- `correctness` - Accuracy vs expected output
- `context_adherence` - Adherence to context
- `context_adherence_luna` - Luna model version
- `context_relevance` - Relevance of retrieved context
- `ground_truth_adherence` - Adherence to ground truth
- `instruction_adherence` - Following instructions

### Content Safety Metrics
- `input_toxicity` - Toxicity in input
- `input_toxicity_luna` - Luna model version
- `output_toxicity` - Toxicity in output
- `output_toxicity_luna` - Luna model version
- `input_sexist` - Sexist content in input
- `input_sexist_luna` - Luna model version
- `output_sexist` - Sexist content in output
- `output_sexist_luna` - Luna model version

### Security Metrics
- `prompt_injection` - Prompt injection detection
- `prompt_injection_luna` - Luna model version
- `input_pii` - PII in input
- `output_pii` - PII in output

### RAG Metrics
- `chunk_attribution_utilization` - Chunk usage in response
- `chunk_attribution_utilization_luna` - Luna model version

### Agentic Metrics
- `agentic_session_success` - Session-level success
- `agentic_workflow_success` - Workflow-level success
- `action_advancement_luna` - Action advancement
- `action_completion_luna` - Action completion
- `tool_error_rate` - Tool execution errors
- `tool_error_rate_luna` - Luna model version
- `tool_selection_quality` - Quality of tool selection
- `tool_selection_quality_luna` - Luna model version

### Tone & Style Metrics
- `input_tone` - Tone of input
- `output_tone` - Tone of output
- `prompt_perplexity` - Prompt complexity
- `uncertainty` - Response uncertainty

### Standard NLP Metrics
- `bleu` - BLEU score for translation quality
- `rouge` - ROUGE score for summarization quality

## Usage Examples

### Basic Usage
```python
from galileo.schema.metrics import GalileoScorers

metrics = [
    GalileoScorers.completeness,
    GalileoScorers.correctness,
    GalileoScorers.output_toxicity
]
```

### In Experiments
```python
from run_experiment import run_galileo_experiment

results = run_galileo_experiment(
    experiment_name="my-experiment",
    dataset_name="my-dataset",
    metrics=[
        GalileoScorers.context_adherence,
        GalileoScorers.completeness,
        GalileoScorers.output_toxicity
    ]
)
```

### In Streamlit UI
The UI provides checkboxes for the most common scorers:
- Context Adherence
- Completeness
- Correctness
- Toxicity (output)
- Chunk Attribution & Utilization

## Dataset Requirements

Different scorers require different fields in your dataset:

### Minimal (input only)
- `output_toxicity`
- `input_toxicity`
- `prompt_injection`
- `input_pii`

### Input + Output
- `completeness`
- `output_pii`
- `output_sexist`

### Input + Output + Expected Output
- `correctness`
- `ground_truth_adherence`

### Input + Output + Context
- `context_adherence`
- `context_relevance`

### RAG-Specific (needs chunks)
- `chunk_attribution_utilization`

## Notes

### Luna vs Standard Models
- Some scorers have both standard and `_luna` versions
- Luna models are newer, fine-tuned evaluation models
- Both versions are available for compatibility

### Common Issues

**Error: `type object 'ScorerName' has no attribute 'X'`**
- The scorer name is incorrect or doesn't exist
- Run `python check_available_scorers.py` to see all options
- Check spelling and capitalization

**Error: Missing required fields**
- Some scorers need specific dataset fields
- See "Dataset Requirements" above
- Add missing fields to your dataset

## Updating Metrics

To add/remove metrics in experiments:

**In Code:**
```python
# run_experiment.py
metrics = [
    GalileoScorers.completeness,
    GalileoScorers.correctness,
    # Add more here
]
```

**In UI:**
- Go to Experiments tab
- Check/uncheck desired metrics
- Run experiment

## References

- [Galileo Metrics Docs](https://v2docs.galileo.ai/concepts/metrics)
- [Galileo Scorers API](https://v2docs.galileo.ai/sdk-api/metrics)
- Run `python check_available_scorers.py` for current list

---

**Last Updated:** Based on Galileo SDK version in requirements.txt  
**Total Scorers:** 83 available

