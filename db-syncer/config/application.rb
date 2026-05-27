require_relative "boot"

require "rails"
require "active_record/railtie"

Bundler.require(*Rails.groups)

module ReoptApi
  class Application < Rails::Application
    config.load_defaults 8.1
    config.autoload_lib(ignore: %w[assets tasks])

    # Use SQL dumps (db/structure.sql) instead of the default Ruby dumps
    # (db/schema.rb). This provides easier dumping of multiple Postgres schemas
    # and other special Postgres types.
    config.active_record.schema_format = :sql
    config.active_record.dump_schemas = :all
  end
end
