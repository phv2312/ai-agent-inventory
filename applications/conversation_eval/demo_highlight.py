import gradio as gr
import pandas as pd


def highlight_snippet(df, keyword1, keyword2):
    def _highlight(cell):
        if pd.isna(cell):
            return cell
        cell_str = str(cell)
        if keyword1:
            cell_str = cell_str.replace(
                keyword1,
                f'<span style="background-color:yellow; color:red; font-weight:bold;">{keyword1}</span>',
            )
        if keyword2:
            cell_str = cell_str.replace(
                keyword2,
                f'<span style="background-color:lightgreen; color:black; font-weight:bold;">{keyword2}</span>',
            )
        return cell_str

    highlighted_df = df.copy()
    highlighted_df["text"] = highlighted_df["text"].map(_highlight)
    return highlighted_df.to_html(escape=False, index=False)


# Sample data
data = {
    "id": [1, 2, 3],
    "text": [
        "Apple is a tech company.",
        "Banana is yellow.",
        "I love eating apple pie and banana cake.",
    ],
}
df = pd.DataFrame(data)

# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("### Highlight Two Keywords with Custom Font Colors")
    with gr.Row():
        keyword1 = gr.Textbox(label="Keyword 1 (Yellow + Red Font)", value="Apple")
        keyword2 = gr.Textbox(label="Keyword 2 (Green + Black Font)", value="banana")
    html_output = gr.HTML()

    def update_html(k1, k2):
        return highlight_snippet(df, k1, k2)

    keyword1.change(fn=update_html, inputs=[keyword1, keyword2], outputs=html_output)
    keyword2.change(fn=update_html, inputs=[keyword1, keyword2], outputs=html_output)

    html_output.value = highlight_snippet(df, "Apple", "banana")

demo.launch()
