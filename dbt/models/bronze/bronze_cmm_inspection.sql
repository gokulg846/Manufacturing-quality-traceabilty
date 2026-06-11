with source as (
    select *
    from read_parquet(
        '{{ var("lakehouse_root") }}/bronze/cmm_inspection/*/*.parquet',
        union_by_name = true
    )
)

select
    cast(inspection_ts as timestamp) as inspection_ts,
    cast(production_date as date) as production_date,
    cast(part_id as varchar) as part_id,
    cast(dimension_name as varchar) as dimension_name,
    cast(measured_value as double) as measured_value,
    cast(nominal as double) as nominal,
    cast(tolerance as double) as tolerance,
    cast(lower_spec_limit as double) as lower_spec_limit,
    cast(upper_spec_limit as double) as upper_spec_limit,
    upper(cast(pass_fail as varchar)) as pass_fail
from source
