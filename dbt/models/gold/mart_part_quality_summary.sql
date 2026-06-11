with scored as (
    select
        p.part_id,
        p.production_date,
        p.process_ts,
        p.part_model,
        p.line_id,
        p.shift,
        p.machine_id,
        p.batch_id,
        m.supplier_id,
        p.spindle_speed,
        p.feed_rate,
        p.coolant_temp,
        p.cycle_time,
        coalesce(c.inspected_dimension_count, 0) as inspected_dimension_count,
        coalesce(c.failed_dimension_count, 0) as failed_dimension_count,
        coalesce(c.any_dimension_out_of_tolerance, false) as any_dimension_out_of_tolerance,
        c.max_dimension_tolerance_utilization,
        coalesce(c.failing_dimension_names, '') as failing_dimension_names,
        coalesce(t.audited_joint_count, 0) as audited_joint_count,
        coalesce(t.failed_joint_count, 0) as failed_joint_count,
        coalesce(t.any_torque_failure, false) as any_torque_failure,
        t.max_torque_error_pct,
        coalesce(t.failing_joint_ids, '') as failing_joint_ids,
        m.hardness,
        m.tensile_strength,
        m.cert_date,
        coalesce(m.any_material_deviation, false) as any_material_deviation,
        coalesce(m.material_failure_reason, 'unknown') as material_failure_reason,
        f.defect_flag,
        f.defect_root_cause,
        case when p.coolant_temp > 34.0 then 1 else 0 end as coolant_process_risk,
        case when p.feed_rate > 710.0 then 1 else 0 end as feed_process_risk
    from {{ ref('silver_part_population') }} as p
    left join {{ ref('silver_cmm_quality') }} as c
        on p.part_id = c.part_id
    left join {{ ref('silver_torque_quality') }} as t
        on p.part_id = t.part_id
    left join {{ ref('silver_material_quality') }} as m
        on p.part_id = m.part_id
    left join {{ ref('silver_part_quality_flags') }} as f
        on p.part_id = f.part_id
)

select
    part_id,
    production_date,
    process_ts,
    part_model,
    line_id,
    shift,
    machine_id,
    batch_id,
    supplier_id,
    spindle_speed,
    feed_rate,
    coolant_temp,
    cycle_time,
    inspected_dimension_count,
    failed_dimension_count,
    any_dimension_out_of_tolerance,
    max_dimension_tolerance_utilization,
    failing_dimension_names,
    audited_joint_count,
    failed_joint_count,
    any_torque_failure,
    max_torque_error_pct,
    failing_joint_ids,
    hardness,
    tensile_strength,
    cert_date,
    any_material_deviation,
    material_failure_reason,
    coalesce(defect_flag, true) as defect_flag,
    coalesce(defect_root_cause, 'unknown') as defect_root_cause,
    cast(
        least(
            100,
            greatest(
                0,
                100
                - failed_dimension_count * 10
                - failed_joint_count * 15
                - case when any_material_deviation then 25 else 0 end
                - coolant_process_risk * 4
                - feed_process_risk * 3
            )
        ) as integer
    ) as composite_quality_score
from scored
