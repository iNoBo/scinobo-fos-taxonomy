"""

This script uses the scientific descriptions of the FoS along with the web descriptions to validate the FoS.
In essence we are going to perform two validations. One with the old taxonomy and one with the new taxonomy.
We are going to provide the scientific and web descriptions of a parent FoS and the scientific and web descriptions of the children FoS.
We are going to ask an LLM whether the children FoS are related to the parent and whether are indeed a subcategory of the parent FoS.
The LLM should provide a structured output with the following format:
{
    "related": boolean,
    "related_explanation": string,
    "subcategory": boolean,
    "subcategory_explanation": "string"
}

"""

