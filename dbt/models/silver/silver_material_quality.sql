with material_by_part as (
    select
        p.part_id,
        p.production_date,
        p.batch_id,
        m.supplier_id,
        m.hardness,
        m.tensile_strength,
        m.cert_date,
        case
            when m.batch_id is null then true
            when m.hardness < m.hardness_min_spec or m.hardness > m.hardness_max_spec then true
            when m.tensile_strength < m.tensile_min_spec or m.tensile_strength > m.tensile_max_spec then true
            else false
        end as any_material_deviation,
        case
            when m.batch_id is null then 'missing_cert'
            when m.hardness < m.hardness_min_spec then 'hardness_low'
            when m.hardness > m.hardness_max_spec then 'hardness_high'
            when m.tensile_strength < m.tensile_min_spec then 'tensile_low'
            when m.tensile_strength > m.tensile_max_spec then 'tensile_high'
            else 'in_spec'
        end as material_failure_reason
    from {{ ref('silver_part_population') }} as p
    left join {{ ref('bronze_supplier_material_certs') }} as m
        on p.batch_id = m.batch_id
)

select *
from material_by_part
