with cmm as (
    select
        part_id,
        production_date,
        dimension_name,
        measured_value,
        nominal,
        tolerance,
        pass_fail,
        abs(measured_value - nominal) / nullif(tolerance, 0) as tolerance_utilization
    from {{ ref('bronze_cmm_inspection') }}
    where part_id is not null
      and dimension_name is not null
)

select
    part_id,
    min(production_date) as production_date,
    count(*) as inspected_dimension_count,
    sum(case when pass_fail = 'FAIL' then 1 else 0 end) as failed_dimension_count,
    max(case when pass_fail = 'FAIL' then true else false end) as any_dimension_out_of_tolerance,
    round(max(tolerance_utilization), 3) as max_dimension_tolerance_utilization,
    string_agg(distinct dimension_name, ', ' order by dimension_name)
        filter (where pass_fail = 'FAIL') as failing_dimension_names
from cmm
group by part_id
