import featureform as ff
from featureform import local

client = ff.Client(local=True)

episodes = local.register_directory(
    name="mlops-episodes",
    path="/Users/wsong/Downloads/allinpodcastAI-master (2)/data1",
    description="Transcripts from recent MLOps episodes",
)


@local.df_transformation(inputs=[episodes])
def process_episode_files(dir_df):
    from io import StringIO
    import pandas as pd

    episode_dfs = []
    for i, row in dir_df.iterrows():
        csv_str = StringIO(row[1])
        r_df = pd.read_csv(csv_str, sep=";")
        r_df["filename"] = row[0]
        episode_dfs.append(r_df)

    return pd.concat(episode_dfs)

@local.df_transformation(inputs=[process_episode_files])
def speaker_primary_key(episodes_df):
    episodes_df["PK"] = episodes_df.apply(lambda row: f"{row['Speaker']}_{row['Start time']}_{row['filename']}", axis=1)
    return episodes_df

@local.df_transformation(inputs=[speaker_primary_key])
def vectorize_comments(episodes_df):
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(episodes_df["Text"].tolist())
    episodes_df["Vector"] = embeddings.tolist()

    return episodes_df

pinecone = ff.register_pinecone(
    name="pinecone",
    project_id="default",
    environment="us-west1-gcp-free",
    api_key="d3070f4d-25a0-4438-8af6-3b264d21a2dd",
)

@ff.entity
class Speaker:
    comment_embeddings = ff.Embedding(
        vectorize_comments[["PK", "Vector"]],
        dims=384,
        vector_db=pinecone,
        description="Embeddings created from speakers' comments in episodes",
        variant="v2"
    )
    comments = ff.Feature(
        speaker_primary_key[["PK", "Text"]],
        type=ff.String,
        description="Speakers' original comments",
        variant="v2"
    )

@ff.ondemand_feature(variant="calhacks")
def relevent_comments(client, params, entity):
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    search_vector = model.encode(params["query"])
    res = client.nearest("comment_embeddings", "v2", search_vector, k=3)
    return res

@ff.ondemand_feature(variant="calhack")
def contextualized_prompt(client, params, entity):
    pks = client.features([("relevent_comments", "calhacks")], {}, params=params)
    prompt = "Use the following snippets from our podcast to answer the following question\n"
    for pk in pks[0]:
        prompt += "```"
        prompt += client.features([("comments", "v2")], {"speaker": pk})[0]
        prompt += "```\n"
    prompt += "Question: "
    prompt += params["query"]
    prompt += "?"
    return prompt

from flask import Flask, request, jsonify
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
@app.route('/api/chat', methods=['POST'])
def handle_user_input():
    user_input = request.json.get('message')
    print(user_input)
    # Process the user input in your Python code
    q = user_input
    client.apply()
    prompt = client.features([("contextualized_prompt", "calhack")], {}, params={"query": q})[0]
    import openai
    openai.organization = "org-ZsjXx3AgIXIWjxr7TGkViTsi"
    openai.api_key = "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"
    answers = (openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=1000, # The max number of tokens to generate
        temperature=1.0 # A measure of randomness
    )["choices"][0]["text"])

    print(answers)
    response = {'message': 'Received user input: {}'.format(answers)}
    return jsonify(response)

if __name__ == '__main__':
    app.run()
'''

q = "How important is it to be premium?"
client.apply()
prompt = client.features([("contextualized_prompt", "calhack")], {}, params={"query": q})[0]

import openai
openai.organization = "org-ZsjXx3AgIXIWjxr7TGkViTsi"
openai.api_key = "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"
print(openai.Completion.create(
    model="text-davinci-003",
    prompt=prompt,
    max_tokens=1000, # The max number of tokens to generate
    temperature=1.0 # A measure of randomness
)["choices"][0]["text"])
'''