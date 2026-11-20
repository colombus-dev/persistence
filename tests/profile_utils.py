"""Test-local helpers to turn a JSON profile fixture into the SQLModel graph.

Mirrors the nesting colombus uses when importing a profile (Profile -> Step ->
MetaInstruction -> Code, plus CellOutput per output id). Kept out of the `app`
package because persistence only stores and exposes profiles; ingestion belongs
to the colombus app.
"""

import uuid

from sqlmodel import Session

from app.db.models import CellOutput, Code, MetaInstruction, Profile, Step
from tests.profile_types import ProfileJson


def ingest_profile(
    session: Session, project_id: uuid.UUID, profile_json: ProfileJson
) -> Profile:
    """Build (and flush) a Profile graph from a JSON profile document."""
    all_steps: list[Step] = []
    all_profile_mi: list[MetaInstruction] = []
    all_profile_codes: list[Code] = []
    previous_step = None
    total_mi_i = 0
    total_c_i = 0

    for se_i, se in enumerate(profile_json["source"]):
        all_metainstructions = []
        for mi in se["tasks"]:
            all_codes = []
            for c in mi["tasks"]:
                all_codes.append(Code(content=c["name"], position=total_c_i))
                total_c_i += 1
            all_metainstructions.append(
                MetaInstruction(
                    algoFamily=mi["algoFamily"],
                    algoName=mi["algoName"],
                    library=mi["library"],
                    function=mi["function"],
                    position=total_mi_i,
                    codes=all_codes,
                    number_children=len(mi["tasks"]),
                )
            )
            all_profile_codes.extend(all_codes)
            total_mi_i += 1

        cell_outputs = [
            CellOutput(image=profile_json["outputs"][output_id])
            for output_id in se["outputs_ids"]
            if output_id in profile_json["outputs"]
        ]
        new_step = Step(
            name=se["name"],
            position=se_i,
            meta_instructions=all_metainstructions,
            number_children=len(se["tasks"]),
            previous_step=previous_step,
            cell_outputs=cell_outputs,
        )
        all_steps.append(new_step)
        previous_step = new_step
        all_profile_mi.extend(all_metainstructions)

    profile = Profile(
        project_id=project_id,
        # colombus stores a NOT NULL score; fixtures that omit a performance
        # score (score: null) fall back to 0.0 so they can still be persisted.
        score=profile_json.get("score") or 0.0,
        name=profile_json["name"],
        steps=all_steps,
        encoded_profile="-".join(step["name"] for step in profile_json["source"]),
        meta_instructions=all_profile_mi,
        codes=all_profile_codes,
        json_profile=profile_json,
    )
    session.add(profile)
    return profile
