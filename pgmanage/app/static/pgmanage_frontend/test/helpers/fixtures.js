// Shared test fixtures for shapes that were hand-duplicated across many
// test files.

// Matches the error shape axios rejects with and handleError() expects:
// { response: { data: { data: message } } }
export function mockErrorResponse(message) {
  return {
    response: {
      data: {
        data: message,
      },
    },
  };
}

// A saved PostgreSQL connection as get_connections returns it.
export function postgresqlConnection(overrides = {}) {
  return {
    id: 1,
    alias: "Test Connection",
    technology: "postgresql",
    group: null,
    conn_string: "",
    server: "127.0.0.1",
    port: "5432",
    service: "postgres",
    user: "postgres",
    password: "",
    password_set: true,
    tunnel: {
      enabled: false,
      server: "",
      port: "",
      user: "",
      password: "",
      password_set: false,
      key: "",
      key_set: false,
    },
    connection_params: { sslmode: "prefer" },
    credentials_extra: {},
    color_label: 0,
    ...overrides,
  };
}

// The form is hidden until its parent picks a connection, which is what fills
// connectionLocal in.
export async function mountConnectionForm(mount, component, connection) {
  const wrapper = mount(component, {
    props: {
      visible: false,
      initialConnection: {},
      technologies: ["postgresql", "rdspostgresql", "mysql"],
    },
  });
  await wrapper.setProps({ visible: true, initialConnection: connection });
  return wrapper;
}
