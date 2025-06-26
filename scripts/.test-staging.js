
      const postgres = require('postgres');
      const sql = postgres('postgresql://neondb_owner:npg_sLKMPmqYzZ21@ep-super-mouse-a8tffxbm-pooler.eastus2.azure.neon.tech/neondb?sslmode=require', {
        ssl: 'require',
        max: 1,
        idle_timeout: 20,
        connect_timeout: 10,
      });
      
      (async () => {
        try {
          const result = await sql`SELECT current_database(), current_user, version()`;
          console.log(JSON.stringify({
            success: true,
            database: result[0].current_database,
            user: result[0].current_user
          }));
          await sql.end();
        } catch (error) {
          console.log(JSON.stringify({
            success: false,
            error: error.message
          }));
          process.exit(1);
        }
      })();
    