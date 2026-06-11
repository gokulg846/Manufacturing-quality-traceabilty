with source as (
    select *
    from read_parquet(
        '{{ var("lakehouse_root") }}/bronze/torque_audit/*/*.parquet',
        union_by_name = true
    )
)

select
    cast(audit_ts as timestamp) as audit_ts,
    cast(production_date as date) as production_date,
    cast(part_id as varchar) as part_id,
    cast(joint_id as varchar) as joint_id,
    cast(target_torque as double) as target_torque,
    cast(actual_torque as double) as actual_torque,
    cast(angle as double) as angle,
    cast(torque_lower_limit as double) as torque_lower_limit,
    cast(torque_upper_limit as double) as torque_upper_limit,
    cast(angle_lower_limit as double) as angle_lower_limit,
    cast(angle_upper_limit as double) as angle_upper_limit,
    upper(cast(pass_fail as varchar)) as pass_fail
from source
