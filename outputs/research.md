# vLLM Tool Calling Capabilities

vLLM supports several methods of function calling within its chat completion API:

1. **Named Function Calling:**
   - Uses structured outputs to ensure the response matches the tool parameter object defined by the JSON schema.
   - Requires defining functions in the `tools` parameter and specifying a `name` in the `tool_choice` parameter.
2. **Required Function Calling (`tool_choice='required'`):**
   - Ensures the model generates one or more tool calls based on the specified tools, with the output strictly following the schema defined in the `tools` parameter.
3. **Automatic Tool Choice (`--enable-auto-tool-choice`):**
   - Enables the model to generate its own tool calls when it deems appropriate.
4. **None Function Calling (`tool_choice='none'`):**
   - Prevents any tool calls, response contains regular text content only.

### Setup Instructions:

- To enable automatic function calling: Use `--enable-auto-tool-choice`, select a `--tool-call-parser`, and optionally specify a chat template with `--chat-template`.
- For Hermes models: Use `--tool-call-parser hermes`
- For Mistral models: Recommended flags include `--tokenizer_mode hf --config_format hf --load_format hf --tool-call-parser mistral --chat-template examples/tool_chat_template_mistral_parallel.jinja`
- For Llama Models (JSON-based): Use `--tool-call-parser llama3_json` and select appropriate chat template.

### Constrained Decoding Behavior:

The behavior of enforcing the tool parameter schema during generation depends on the `tool_choice` mode. Named function calling and required modes enforce the schema, while automatic mode does not constrain decoding and relies on a parser to extract tool calls from raw text output.