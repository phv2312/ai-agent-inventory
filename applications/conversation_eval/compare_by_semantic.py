import aiofiles
from jinja2 import Template
import pandas as pd

from agent.container import Container
from agent.models.messages import UserMessage
from agent.programs.impl.semantic_comparison import (
    SemanticComparisonProgram,
    SemanticComparisonResponse,
)


container = Container()


program = SemanticComparisonProgram(
    api_key=container.env.openai_api_key,
    api_version=container.env.openai_api_version,
    azure_endpoint=container.env.openai_azure_endpoint,
    deployment_name=container.env.openai_chat_deployment_name,
)


async def main():
    first_sentence = """
Bây giờ mình sẽ điền thông tin đăng ký vay. Ứng dụng sẽ chuyển đến màn hình -\n Thông tin khoản -\n vay. Đến bước này, mình sẽ chọn hạn mức vay mong muốn. +\n Ứng dụng sẽ hiển thị số tiền tối đa chị có thể vay, mình có thể điều chỉnh trong khoảng đó ạ. Trên màn hình Thời hạn vay đang là 60 tháng, mình sửa lại Thời hạn vay đúng như em tư vấn -\n nha
"""
    second_sentence = """
Dạ, em ghi nhận ạ. giờ mình sẽ điền thông tin đăng ký vay. Ứng dụng sẽ chuyển đến màn hình "Thông -\n tin khoản vay". -\n Đến bước này, chị chọn hạn mức vay mong muốn +\n là 35 triệu nha. -\n
"""
    prompt_path = "agent/prompts/conversation_eval/semantic_comparison.md"
    excel_path = "Book1.xlsx"
    excel_path_out = "Book1_out_1315.xlsx"

    async with aiofiles.open(prompt_path, "r") as file:
        template = Template(await file.read())

    df = pd.read_excel(excel_path)
    predicts: list[SemanticComparisonResponse] = []
    for index, row in df.iterrows():
        print(f"{index + 1}/{len(df)}")
        first_sentence = row["rule_constant"]
        second_sentence = row["message"]

        rendered_template = template.render(
            first_sentence=first_sentence.strip(),
            second_sentence=second_sentence.strip(),
        )

        response = await program.aprocess(
            message=UserMessage(content=rendered_template)
        )

        predicts.append(response)

    df["is_same_meaning"] = [predict.is_same_meaning for predict in predicts]
    df["reason"] = [predict.reason for predict in predicts]

    df.to_excel(excel_path_out, index=False)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
