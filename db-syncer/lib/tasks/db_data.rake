# frozen_string_literal: true

namespace :db do
  namespace :data do
    desc "Dump database data for this application from production."
    task dump: :environment do
      require "db-syncer"
      dump_env = ENV["DUMP_ENV"] || Rails.env
      VaultEnvSecrets.load(env: {"DB_SYNCER" => "true", "APP_ENV" => dump_env})
      dump = DbSyncer::Dump.new(dump_env, upload: ":s3:nrel-tada-reopt-files/private/ci/api/db_data_dump.tar")

      # Exclude all table data by default, since we will only import subsets of
      # data.
      exclude_data_tables = [
        "reopt_api.*",
      ]

      # Subset the API run data that we include in the dump so that it's a more
      # mangeable size for local development and staging restores.
      #
      # Include API runs (and all of the associated data for those runs) for:
      #
      # - All runs from the past 15 days.
      # - From the past year, runs from every 26th day (this roughly
      #   corresponds to another half month worth of data, while picking a
      #   non-7 based interaval ensures coverage over different days of the
      #   week throughout the year).
      subset_all_days = 15
      subset_sample_days = 365
      subset_sample_frequency = 26
      subset_data = []
      begin
        # Create a temporary table with all of the subsetted run IDs to dump.
        # Since the subset process runs in separate transactions, we'll dump
        # all of these to a real table (that we'll later drop) that the other
        # queries can reference.
        begin
          original_env = Rails.env
          ActiveRecord::Base.establish_connection(dump_env.to_sym)
          ActiveRecord::Base.connection.execute <<~SQL
            CREATE TABLE public.temp_db_syncer_subset_apimeta AS (
              SELECT id, run_uuid
              FROM reopt_api.reoptjl_apimeta
              WHERE
                created >= date_trunc('day', now() - interval '#{subset_all_days} days')
                OR (
                  created >= date_trunc('day', now() - interval '#{subset_sample_days} days')
                  AND extract(doy FROM created)::integer % #{subset_sample_frequency} = 1
                )
            )
          SQL
        ensure
          ActiveRecord::Base.establish_connection(original_env.to_sym)
        end

        # Dump the `reoptjl_apimeta` table itself.
        subset_tables = [
          "reoptjl_apimeta",
        ]
        subset_data += subset_tables.map do |table_name|
          {
            :table => "reopt_api.#{table_name}",
            :query => <<~SQL
              SELECT #{table_name}.*
              FROM reopt_api.#{table_name}
              WHERE #{table_name}.id IN (SELECT id FROM public.temp_db_syncer_subset_apimeta)
            SQL
          }
        end

        # Dump all of the child tables that are tied to the `reoptjl_apimeta` via
        # a `meta_id` foreign key.
        subset_meta_tables = [
          "reoptjl_absorptionchillerinputs",
          "reoptjl_absorptionchilleroutputs",
          "reoptjl_ashpspaceheaterinputs",
          "reoptjl_ashpspaceheateroutputs",
          "reoptjl_ashpwaterheaterinputs",
          "reoptjl_ashpwaterheateroutputs",
          "reoptjl_boilerinputs",
          "reoptjl_boileroutputs",
          "reoptjl_chpinputs",
          "reoptjl_chpoutputs",
          "reoptjl_coldthermalstorageinputs",
          "reoptjl_coldthermalstorageoutputs",
          "reoptjl_coolingloadinputs",
          "reoptjl_coolingloadoutputs",
          "reoptjl_cstinputs",
          "reoptjl_cstoutputs",
          "reoptjl_domestichotwaterloadinputs",
          "reoptjl_electricheaterinputs",
          "reoptjl_electricheateroutputs",
          "reoptjl_electricloadinputs",
          "reoptjl_electricloadoutputs",
          "reoptjl_electricstorageinputs",
          "reoptjl_electricstorageoutputs",
          "reoptjl_electrictariffinputs",
          "reoptjl_electrictariffoutputs",
          "reoptjl_electricutilityinputs",
          "reoptjl_electricutilityoutputs",
          "reoptjl_existingboilerinputs",
          "reoptjl_existingboileroutputs",
          "reoptjl_existingchillerinputs",
          "reoptjl_existingchilleroutputs",
          "reoptjl_financialinputs",
          "reoptjl_financialoutputs",
          "reoptjl_generatorinputs",
          "reoptjl_generatoroutputs",
          "reoptjl_ghpinputs",
          "reoptjl_ghpoutputs",
          "reoptjl_heatingloadoutputs",
          "reoptjl_hightempthermalstorageinputs",
          "reoptjl_hightempthermalstorageoutputs",
          "reoptjl_hotthermalstorageinputs",
          "reoptjl_hotthermalstorageoutputs",
          "reoptjl_message",
          "reoptjl_outageoutputs",
          "reoptjl_processheatloadinputs",
          "reoptjl_pvinputs",
          "reoptjl_pvoutputs",
          "reoptjl_reoptjlmessageoutputs",
          "reoptjl_settings",
          "reoptjl_siteinputs",
          "reoptjl_siteoutputs",
          "reoptjl_spaceheatingloadinputs",
          "reoptjl_steamturbineinputs",
          "reoptjl_steamturbineoutputs",
          "reoptjl_userprovidedmeta",
          "reoptjl_windinputs",
          "reoptjl_windoutputs",
        ]
        subset_data += subset_meta_tables.map do |table_name|
          {
            :table => "reopt_api.#{table_name}",
            :query => <<~SQL
              SELECT #{table_name}.*
              FROM reopt_api.#{table_name}
              WHERE #{table_name}.meta_id IN (SELECT id FROM public.temp_db_syncer_subset_apimeta)
            SQL
          }
        end

        # Dump all of the child tables that are tied to the `reoptjl_apimeta` via
        # a `run_uuid` foreign key.
        subset_meta_uuid_tables = [
          "reoptjl_portfoliounlinkedruns",
          "reoptjl_userunlinkedruns",
        ]
        subset_data += subset_meta_uuid_tables.map do |table_name|
          {
            :table => "reopt_api.#{table_name}",
            :query => <<~SQL
              SELECT #{table_name}.*
              FROM reopt_api.#{table_name}
              WHERE #{table_name}.run_uuid IN (SELECT run_uuid FROM public.temp_db_syncer_subset_apimeta)
            SQL
          }
        end

        dump.dump({
          schemas: ["reopt_api"],
          exclude_data_tables: exclude_data_tables,
          subset_data: subset_data,
        })
      ensure
        # Cleanup the temporary table of subsetted IDs.
        begin
          original_env = Rails.env
          ActiveRecord::Base.establish_connection(dump_env.to_sym)
          ActiveRecord::Base.connection.execute "DROP TABLE IF EXISTS public.temp_db_syncer_subset_apimeta"
        ensure
          ActiveRecord::Base.establish_connection(original_env.to_sym)
        end
      end
    end

    desc "Restore a production database dump to the local environment."
    task :restore do
      require "db-syncer"
      VaultEnvSecrets.load(env: {"DB_SYNCER" => "true"})
      DbSyncer::Restore.new(download: ":s3:nrel-tada-reopt-files/private/ci/api/db_data_dump.tar") do |restore|
        # Load schemas, dropping any previous tables.
        restore.restore_dump(File.join(restore.dir, "schemas.pgdump.zst"),
          exclude_list: [
            # Exclude extensions that might be present in the production dump,
            # but aren't necessary for development (and might not be present in
            # everyone's dev environment).
            "EXTENSION - pg_repack",
            "COMMENT - EXTENSION pg_repack",
            "EXTENSION - pg_stat_statements",
            "COMMENT - EXTENSION pg_stat_statements",
            "bucardo_",
            "USER MAPPING - USER MAPPING postgres",
          ],
        )

        restore.restore_sql(File.join(restore.dir, "subset_data.sql.zst"))
      end
    end
  end
end

# Since this isn't running in a normal, full Rails environment, fake some tasks
# that the db-syncer gem expects to exist so they don't perform anything.
[
  "db:migrate",
  "db:seed",
  "db:structure:dump",
  "db:test:prepare",
].each do |task_name|
  Rake::Task.define_task(task_name)
  Rake::Task[task_name].clear
end
