select
    p.part_id,
    p.production_date,
    coalesce(c.any_dimension_out_of_tolerance, false) as any_dimension_out_of_tolerance,
    coalesce(t.any_torque_failure, false) as any_torque_failure,
    coalesce(m.any_material_deviation, false) as any_material_deviation,
    case
        when c.part_id is null or t.part_id is null or m.part_id is null then true
        when coalesce(c.any_dimension_out_of_tolerance, false)
          or coalesce(t.any_torque_failure, false)
          or coalesce(m.any_material_deviation, false) then true
        else false
    end as defect_flag,
    case
        when coalesce(c.any_dimension_out_of_tolerance, false) then 'dimension'
        when coalesce(t.any_torque_failure, false) then 'torque'
        when coalesce(m.any_material_deviation, false) then 'material'
        when c.part_id is null or t.part_id is null or m.part_id is null then 'unknown'
        else 'none'
    end as defect_root_cause
from {{ ref('silver_part_population') }} as p
left join {{ ref('silver_cmm_quality') }} as c
    on p.part_id = c.part_id
left join {{ ref('silver_torque_quality') }} as t
    on p.part_id = t.part_id
left join {{ ref('silver_material_quality') }} as m
    on p.part_id = m.part_id
