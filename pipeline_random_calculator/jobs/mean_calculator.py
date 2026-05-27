from dagster import (
    define_asset_job,
    failure_hook,
    success_hook,
)


@success_hook(required_resource_keys={"provenance"})
def mark_execution_success(context):
    # In this linear pipeline, mean_asset is the final step.
    if context.op.name == "mean_asset":
        context.resources.provenance.record_success(context.run_id)


@failure_hook(required_resource_keys={"provenance"})
def mark_execution_failure(context):
    error_message = str(context.op_exception) if context.op_exception else None
    context.resources.provenance.record_failure(context.run_id, error_message)

mean_calculator_job = define_asset_job(
    name="mean_calculadora_job",
    selection=["provenance_asset", "random_numbers_asset", "mean_asset"],
    hooks={mark_execution_success, mark_execution_failure},
)
