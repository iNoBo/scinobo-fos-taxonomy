"""
This script is responsible for connecting to our langfuse installation where we have logged the results of the
validate.py module. We will retrieve the results and calculate some basic metrics for the validation process.
"""

import json
import os
import argparse

from langfuse import Langfuse
from langfuse.api.resources.commons.errors.unauthorized_error import UnauthorizedError
from tqdm import tqdm


def parse_args():
    ##############################################
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--user_id",
        type=str,
        required=True
    ),
    parser.add_argument(
        "--opath",
        type=str,
        help="Path to save the metrics results",
    )
    args = parser.parse_args()
    return args
    ##############################################
    
    
def set_langfuse():
    try:
        langfuse = Langfuse() # no need to pass the host, port, public key, and secret key since they are already set in the config
        langfuse.auth_check()
    except UnauthorizedError:
        print(
            "Langfuse credentials incorrect. Please re-enter your Langfuse credentials in the pipeline settings."
        )
    except Exception as e:
        print(f"Langfuse error: {e} Please re-enter your Langfuse credentials in the pipeline settings.")
    return langfuse


def trace_pagination(langfuse, user_id, limit=50, page=1):
    return langfuse.fetch_traces(limit=limit, page=page, user_id=user_id)


def main():
    # parse arguments
    args = parse_args()
    user_id = args.user_id
    opath = args.opath
    # initialize langfuse
    langfuse = set_langfuse()
    all_traces = []
    page = 1
    limit = 50
    while True:
        traces = trace_pagination(langfuse, user_id, limit, page)
        if len(traces.data) < limit:
            # we are at the last page
            all_traces.extend(traces.data)
            break
        all_traces.extend(traces.data)
        page += 1
    # calculate metrics
    my_list = []
    observed_l3, observed_l4, total_observed_pairs, total_related, total_subcategory = set(), set(), set(), 0, 0
    for trace in tqdm(all_traces, desc="Calculating metrics"):
        # get the observation
        observation = langfuse.fetch_observation(trace.observations[0]) # each trace has only one observation
        output = observation.data.output
        related, subcategory = output["related"], output["subcategory"] # these are boolean values
        l3, l4 = trace.name.split("-")[2], trace.name.split("-")[3] if len(trace.name.split("-")) == 5 else '-'.join(trace.name[3:-1])
        observed_l3.add(l3)
        observed_l4.add(l4)
        total_observed_pairs.add((l3, l4))
        my_list.append((l3, l4))
        total_related += related
        total_subcategory += subcategory
    # save the metrics
    metrics = {
        "observed_l3": len(observed_l3),
        "observed_l4": len(observed_l4),
        "total_observed_pairs": len(total_observed_pairs),
        "total_related": total_related,
        "total_subcategory": total_subcategory,
        "total_unrelated": len(total_observed_pairs) - total_related,
        "total_non_subcategory": len(total_observed_pairs) - total_subcategory,
        "total_related_non_subcategory": total_related - total_subcategory
    }
    with open(opath, "w") as f:
        json.dump(metrics, f, indent=4)
        
        
        
        
    


if __name__ == "__main__":
    main()