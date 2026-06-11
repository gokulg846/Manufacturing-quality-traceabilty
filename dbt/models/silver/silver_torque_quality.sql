with torque as (
    select
        part_id,
        production_date,
        joint_id,
        target_torque,
        actual_torque,
        angle,
        pass_fail,
        abs(actual_torque - target_torque) / nullif(target_torque, 0) as torque_error_pct
    from {{ ref('bronze_torque_audit') }}
    where part_id is not null
      and joint_id is not null
)

select
    part_id,
    min(production_date) as production_date,
    count(*) as audited_joint_count,
    sum(case when pass_fail = 'FAIL' then 1 else 0 end) as failed_joint_count,
    max(case when pass_fail = 'FAIL' then true else false end) as any_torque_failure,
    round(max(torque_error_pct), 4) as max_torque_error_pct,
    string_agg(distinct joint_id, ', ' order by joint_id)
        filter (where pass_fail = 'FAIL') as failing_joint_ids
from torque
group by part_id
