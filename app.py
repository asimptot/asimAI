from flask import Flask, render_template, request, jsonify
from g4f.client import Client
import g4f, os, warnings

warnings.filterwarnings("ignore")

app = Flask(__name__)
client = Client()
messages = []


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/check-grammar", methods=["POST"])
def check_grammar():
    input_text = request.form.get("text", "")
    try:
        prompt = "Check the grammar in the following sentence and return only the corrected version."
        combined_input = f"{prompt} {input_text}"

        response = client.chat.completions.create(
            model=g4f.models.gpt_4o_mini,
            messages=[{"role": "user", "content": combined_input}],
        )

        corrected_text = response.choices[0].message.content
        return jsonify({"corrected_text": corrected_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/translate", methods=["POST"])
def translate_text():
    input_text = request.form.get("text", "")
    target_language = request.form.get("language", "")

    if not target_language:
        return jsonify({"error": "No target language provided"}), 400

    try:
        prompt = (
            f"Translate the following sentence to {target_language}: {input_text}. Please do not remark your "
            f"comment on this translation. Just return the result. "
        )

        response = client.chat.completions.create(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": prompt}],
        )

        translated_text = response.choices[0].message.content
        return jsonify({"translated_text": translated_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/bug-control", methods=["POST"])
def bug_control():
    description_input = request.form.get("description", "")
    prompt = (
        "Check and improve the following bug description. Provide a corrected version with title, priority (1-5), "
        "and severity (1-5). Priority 1 is highest. Please do not write anything and just send me what you changed. "
        "Do not use ** "
    )
    combined_input = f"{prompt}\n\n{description_input}"

    try:
        response = client.chat.completions.create(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": combined_input}],
        )

        result = response.choices[0].message.content
        return jsonify({"bug_description": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/generate-image", methods=["POST"])
def generate_image():
    user_prompt = request.form.get("prompt", "")

    if not user_prompt:
        return jsonify({"error": "Prompt is required"}), 400

    try:
        response = client.chat.completions.create(
            model=g4f.models.dall_e_3,
            messages=[{"role": "user", "content": user_prompt}],
        )

        image_url = response.choices[0].message.content.strip()
        return jsonify({"image_url": image_url})
    except Exception as e:
        return jsonify({"error": f"Error generating image: {str(e)}"}), 500


@app.route("/transcribe-image", methods=["POST"])
def transcribe_image():
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        image_file = request.files["image"]
        image_path = os.path.join("temp", image_file.filename)
        image_file.save(image_path)

        with open(image_path, "rb") as file:
            response = client.chat.completions.create(
                model=g4f.models.gemini_pro,
                messages=[{"role": "user", "content": "Can you transcribe this image? "}],
                image=file,
            )

        analysis_result = response.choices[0].message.content

        os.remove(image_path)

        return jsonify({"transcribe": analysis_result})
    except Exception as e:
        return jsonify({"error": f"Error analyzing image: {str(e)}"}), 500


@app.route("/interactive-chat", methods=["POST"])
def interactive_chat():
    global messages
    user_input = request.form.get("message", "").strip()

    if user_input.lower() == "exit":
        return jsonify({"response": "Exiting chat...", "exit": True})

    try:
        messages.append({"role": "user", "content": user_input})

        if "file" in request.files:
            uploaded_file = request.files["file"]
            file_extension = uploaded_file.filename.split(".")[-1].lower()

            if file_extension in ["jpg", "jpeg", "png", "gif"]:
                image_path = os.path.join("temp", uploaded_file.filename)
                uploaded_file.save(image_path)

                with open(image_path, "rb") as file:
                    response = client.chat.completions.create(
                        messages=messages,
                        model=g4f.models.gpt_4,
                        image=file,
                    )

                os.remove(image_path)

            elif file_extension == "xml":
                xml_path = os.path.join("temp", uploaded_file.filename)
                uploaded_file.save(xml_path)

                with open(xml_path, "r") as file:
                    xml_content = file.read()
                    messages.append({"role": "user", "content": xml_content})

                    response = client.chat.completions.create(
                        messages=messages,
                        model=g4f.models.gpt_4,
                    )

                os.remove(xml_path)

            else:
                return jsonify({"error": "Unsupported file type."}), 400
        else:
            response = client.chat.completions.create(
                messages=messages,
                model=g4f.models.gpt_35_turbo,
            )

        gpt_response = response.choices[0].message.content
        messages.append({"role": "assistant", "content": gpt_response})
        return jsonify({"response": gpt_response})
    except Exception as e:
        return jsonify({"error": f"Error during interactive chat: {str(e)}"}), 500


@app.route("/add-testcases", methods=["POST"])
def add_testcase():
    requirements_text = request.form.get("requirements", "")
    input_text = request.form.get("text", "")
    try:
        prompt = (
            "Analyze the requirements and code below. Add extensive happy flow and unhappy flow new test cases for the "
            "following code to cover all branches. Provide them as TC-1, TC-2, etc. in a table view. Please only share "
            "Test Case ID, Description and Expected Outcome on the output table. You don't have to limit test cases "
            "with 10. Do not print any Spanish text. Do not share besides that. "
            "Do not include any headers or additional text in the output. "
            "Format the output as a markdown table without repeating headers or any additional lines. "
            "Only provide the data rows without titles. "
            "The first row should be: 'Test Case ID | Description | Expected Outcome' and no other headers should be included."
        )
        combined_input = (
            f"{prompt}\n\nRequirements:\n{requirements_text}\n\nCode:\n{input_text}"
        )
        response = client.chat.completions.create(
            model=g4f.models.claude_3_5_sonnet,
            messages=[{"role": "user", "content": combined_input}],
        )
        corrected_text = response.choices[0].message.content.strip()

        lines = corrected_text.splitlines()
        new_test_cases = "\n".join(lines[1:])

        return jsonify({"test_cases": new_test_cases})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/how-to-reply", methods=["POST"])
def how_to_reply():
    input_text = request.form.get("text", "")
    try:
        prompt = "Reply to the following sentence and return only the answer. "
        combined_input = f"{prompt} {input_text}"

        response = client.chat.completions.create(
            model=g4f.models.gpt_35_turbo,
            messages=[{"role": "user", "content": combined_input}],
        )

        corrected_text = response.choices[0].message.content
        return jsonify({"Reply": corrected_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/process-requirements-and-code", methods=["POST"])
def process_requirements_and_code():
    requirements = request.form.get("requirements", "")
    code = request.form.get("code", "")

    try:
        predefined_instruction = (
            "Analyze the requirements and code below. Validate if the requirements are fulfilled by the code "
            "and provide suggestions for improvement or missing elements. Return only the answer. "
        )
        combined_input = f"{predefined_instruction}\n\nRequirements:\n{requirements}\n\nCode:\n{code}"

        response = client.chat.completions.create(
            model=g4f.models.claude_3_5_sonnet,
            messages=[{"role": "user", "content": combined_input}],
        )

        analysis_result = response.choices[0].message.content
        return jsonify({"analysis": analysis_result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/recommend-cafe", methods=["POST"])
def recommend_cafe():
    zip_code_1 = request.form.get("zip_code_1", "")
    zip_code_2 = request.form.get("zip_code_2", "")
    country_1 = request.form.get("country_1", "")
    country_2 = request.form.get("country_2", "")
    venue_type = request.form.get("venue_type", "cafe")

    try:
        prompt = (
            f"I will be meeting you between the postcodes from {country_1} {zip_code_1} and from {country_2} {zip_code_2}. "
            f"Can you recommend me a {venue_type} for the meeting? Let it be a middle point. "
            "Please just write the meeting city, the name and the address of the venue."
        )

        response = client.chat.completions.create(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": prompt}],
        )

        recommendation = response.choices[0].message.content
        return jsonify({"recommendation": recommendation})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/trip-planner", methods=["POST"])
def trip_planner():
    city_or_country = request.form.get("location", "")
    start_date = request.form.get("start_date", "")
    end_date = request.form.get("end_date", "")

    if not city_or_country or not start_date or not end_date:
        return jsonify({"error": "Location and date range are required."}), 400

    try:
        prompt = (
            f"Can you make me a trip plan for {city_or_country}, including where to eat and drink locally, "
            f"as well as special locations to visit? I have a trip planned from {start_date} to {end_date}. "
            "Please return the result in a table view with the following columns: Date, Activity/Location, "
            "Description/Notes, Dining Options, Events/Highlights. Do not include any headers or additional text. "
            "Just provide the data rows without any titles."
        )

        response = client.chat.completions.create(
            model=g4f.models.gpt_4,
            messages=[{"role": "user", "content": prompt}],
        )

        trip_plan = response.choices[0].message.content
        return jsonify({"trip_plan": trip_plan})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
