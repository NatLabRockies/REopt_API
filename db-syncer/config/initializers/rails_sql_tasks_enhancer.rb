RailsSqlTasksEnhancer.add(:setup, "task_setup.sql.erb", after_load: true, before_migrate: Rails.env.local?)
RailsSqlTasksEnhancer.add(:setup_grants, "task_grants.sql.erb", after_load: true, after_migrate: true)
