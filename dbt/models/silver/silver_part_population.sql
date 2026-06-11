select
    part_id,
    production_date,
    process_ts,
    part_model,
    line_id,
    shift,
    machine_id,
    batch_id,
    spindle_speed,
    feed_rate,
    coolant_temp,
    cycle_time
from {{ ref('bronze_process_parameters') }}
where part_id is not null
  and batch_id is not null
