CREATE TABLE sakura_users(
user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
email VARCHAR(50) UNIQUE NOT NULL,
password_hash VARCHAR(50),
name VARCHAR(50) NOT NULL,
user_type VARCHAR(10) NOT NULL,
language_level language_level NOT NULL,
cohort_cid UUID REFERENCES sakura_cohorts(cohort_id) ON DELETE SET NULL,
created_at TIMESTAMP DEFAULT current_timestamp,
last_login TIMESTAMP,
status VARCHAR(10) DEFAULT 'active');

CREATE TABLE sakura_cohorts(
cohort_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
name VARCHAR(50) NOT NULL,
admin_id UUID NOT NULL REFERENCES sakura_users(user_id) ON DELETE CASCADE,
start_date DATE NOT NULL,
expected_end_date DATE NOT NULL,
targer_job_readiness_score INTEGER DEFAULT 75,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE sakura_cohorts ADD CONSTRAINT fk_user_id FOREIGN KEY (admin_id) REFERENCES sakura_users(user_id) ON DELETE SET NULL;

CREATE TABLE sakura_scenarios(
scenario_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
name VARCHAR(50) NOT NULL,
description TEXT NOT NULL,
level language_level NOT NULL,
job_domain VARCHAR(50) NOT NULL,
sample_scenario JSON,
grammer_focus JSON,
cultural_notes JSON,
is_active BOOLEAN DEFAULT 'TRUE'
);

ALTER TABLE sakura_scenarios add column created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

CREATE TABLE sakura_users_attempts(
attempt_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
user_id UUID REFERENCES sakura_users(user_id) ON DELETE SET NULL,
scenario_id UUID REFERENCES sakura_scenarios(scenario_id) ON DELETE SET NULL,
start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
end_time TIMESTAMP,
completion_status completion_status_options,
exchanges JSON NOT NULL DEFAULT '[]'::json,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

CREATE INDEX idx_users_email ON sakura_users(email);
CREATE INDEX idx_users_cohort_id ON sakura_users(cohort_id);
CREATE INDEX idx_attempts_user_id ON sakura_users_attempts(user_id);
CREATE INDEX idx_attempts_scenario_id ON sakura_users_attempts(scenario_id);
CREATE INDEX idx_attempts_user_scenario ON sakura_users_attempts(user_id, scenario_id);
CREATE INDEX idx_scores_user_id ON user_scores(user_id);
CREATE INDEX idx_scores_scenario_id ON user_scores(scenario_id);

create type completion_status as ENUM('completed','abandoned','in progress')

CREATE TABLE user_scores(
score_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
user_id UUID NOT NULL REFERENCES sakura_users(user_id),
scenario_id UUID NOT NULL REFERENCES sakura_scenarios(scenario_id),
grammar_score INTEGER,
politeness_score INTEGER,
clarity_score INTEGER,
cultural_correctness_score INTEGER,
overall_score INTEGER,
job_readiness_level language_level,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE progress_summary(
user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
total_scenarios_completed INTEGER,
current_level language_level,
days_trained INTEGER,
avg_grammer_score INTEGER,
avg_politeness_score INTEGER,
weak_areas JSON,
job_readiness_percentage INTEGER
);

create type language_level as ENUM('N5','N4','N3','N2','N1');

create table voice_interview(interview_id UUID default gen_random_uuid() PRIMARY KEY,user_id UUID REFERENCES sakura_users(user_id),scenario_id UUID REFERENCES sakura_scenarios(scenario_id),started_at TIMESTAMP ,ended_at TIMESTAMP,overall_score NUMERIC,jlpt_level language_level,pronounciation_level NUMERIC,grammer_score NUMERIC,flow_score NUMERIC,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

CREATE TABLE voice_exchange(exhange_id UUID DEFAULT gen_random_uuid(),interview_id UUID REFERENCES voice_interview(interview_id),turn_number INTEGER,manager_question_text TEXT,manager_question_romaji TEXT,candidate_audio_path TEXT,candidate_script TEXT,pronounciation_score DECIMAL,grammer_score DECIMAL,flow_score DECIMAL,manager_feedback TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

alter table public.voice_interview alter column status TYPE public.completion_status_options USING status::text::public.completion_status_options;