with source as (
    select *
    from read_parquet(
        '{{ var("lakehouse_root") }}/bronze/supplier_material_certs/*/*.parquet',
        union_by_name = true
    )
)

select
    cast(batch_id as varchar) as batch_id,
    cast(supplier_id as varchar) as supplier_id,
    cast(hardness as double) as hardness,
    cast(tensile_strength as double) as tensile_strength,
    cast(cert_date as date) as cert_date,
    cast(hardness_min_spec as double) as hardness_min_spec,
    cast(hardness_max_spec as double) as hardness_max_spec,
    cast(tensile_min_spec as double) as tensile_min_spec,
    cast(tensile_max_spec as double) as tensile_max_spec,
    cast(material_deviation as boolean) as material_deviation
from source
