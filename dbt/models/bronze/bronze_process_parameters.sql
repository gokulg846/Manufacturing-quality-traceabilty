with source as (
    select *
    from read_parquet(
        '{{ var("lakehouse_root") }}/bronze/process_parameters/*/*.parquet',
        union_by_name = true
    )
)

select
    cast(process_ts as timestamp) as process_ts,
    cast(production_date as date) as production_date,
    cast(part_id as varchar) as part_id,
    cast(part_model as varchar) as part_model,
    cast(line_id as varchar) as line_id,
    cast(shift as varchar) as shift,
    cast(machine_id as varchar) as machine_id,
    cast(batch_id as varchar) as batch_id,
    cast(spindle_speed as double) as spindle_speed,
    cast(feed_rate as double) as feed_rate,
    cast(coolant_temp as double) as coolant_temp,
    cast(cycle_time as double) as cycle_time
from source
