alter table match_predictions
    add column if not exists p_over_2_5 numeric(6,5),
    add column if not exists lambda_home numeric(5,3),
    add column if not exists lambda_away numeric(5,3);
