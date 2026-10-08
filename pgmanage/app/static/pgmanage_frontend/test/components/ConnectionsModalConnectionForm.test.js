import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount } from "@vue/test-utils";
import ConnectionsModalConnectionForm from "@src/components/ConnectionsModalConnectionForm.vue";
import { mountConnectionForm, postgresqlConnection } from "../helpers/fixtures.js";

vi.mock("bootstrap", () => ({
  Modal: { getOrCreateInstance: vi.fn(() => ({ hide: vi.fn(), show: vi.fn() })) },
}));

const rdsConnection = (overrides = {}) =>
  postgresqlConnection({
    technology: "rdspostgresql",
    server: "mydb.abc123.us-east-1.rds.amazonaws.com",
    ...overrides,
  });

describe("ConnectionsModalConnectionForm", () => {
  let wrapper;

  beforeEach(async () => {
    wrapper = await mountConnectionForm(
      mount, ConnectionsModalConnectionForm, postgresqlConnection()
    );
  });

  it("does not report a change on load", () => {
    expect(wrapper.vm.isChanged).toBe(false);
  });

  it("shows no AWS fields for plain postgresql", () => {
    expect(wrapper.vm.isRdsPostgresql).toBe(false);
    expect(wrapper.find("#connectionPassword").exists()).toBe(true);
    expect(wrapper.find("#awsRegion").exists()).toBe(false);
  });

  it("offers the postgresql SSL modes to an RDS connection", async () => {
    wrapper = await mountConnectionForm(
      mount, ConnectionsModalConnectionForm, rdsConnection()
    );

    expect(wrapper.vm.sslModes).toEqual(wrapper.vm.postgresql_ssl_modes);
    expect(wrapper.find("#connectionSSL").exists()).toBe(true);
  });

  it("shows password and AWS fields together for an RDS connection", async () => {
    wrapper = await mountConnectionForm(
      mount, ConnectionsModalConnectionForm, rdsConnection({ password_set: false })
    );

    expect(wrapper.find("#connectionPassword").exists()).toBe(true);
    expect(wrapper.find("#awsRegion").exists()).toBe(true);
    expect(wrapper.find("#accessKeyId").exists()).toBe(true);
    expect(wrapper.find("#secretAccessKey").exists()).toBe(true);

    expect(wrapper.find("#connectionPassword").attributes("disabled")).toBeUndefined();
    expect(wrapper.find("#awsRegion").attributes("disabled")).toBeUndefined();
  });

  it("disables the AWS fields once a password is set", async () => {
    wrapper = await mountConnectionForm(
      mount, ConnectionsModalConnectionForm, rdsConnection({ password_set: true })
    );

    expect(wrapper.vm.passwordAuthInUse).toBe(true);
    expect(wrapper.find("#awsRegion").attributes("disabled")).toBeDefined();
    expect(wrapper.find("#accessKeyId").attributes("disabled")).toBeDefined();
    expect(wrapper.find("#secretAccessKey").attributes("disabled")).toBeDefined();
  });

  it("disables the password once an access key is typed", async () => {
    wrapper = await mountConnectionForm(
      mount, ConnectionsModalConnectionForm, rdsConnection({ password_set: false })
    );

    expect(wrapper.find("#connectionPassword").attributes("disabled")).toBeUndefined();

    await wrapper.find("#accessKeyId").setValue("key-id");

    expect(wrapper.vm.iamAuthInUse).toBe(true);
    expect(wrapper.find("#connectionPassword").attributes("disabled")).toBeDefined();
  });

  it("disables the password once a region is stored", async () => {
    wrapper = await mountConnectionForm(
      mount,
      ConnectionsModalConnectionForm,
      rdsConnection({
        password_set: false,
        credentials_extra: { aws_region: "us-east-1" },
      })
    );

    expect(wrapper.vm.iamAuthInUse).toBe(true);
    expect(wrapper.find("#connectionPassword").attributes("disabled")).toBeDefined();
    expect(wrapper.find("#awsRegion").element.value).toBe("us-east-1");
  });

  it("emptying the region frees the password again", async () => {
    wrapper = await mountConnectionForm(
      mount,
      ConnectionsModalConnectionForm,
      rdsConnection({
        password_set: false,
        credentials_extra: { aws_region: "us-east-1", access_key_id: "" },
      })
    );

    expect(wrapper.find("#connectionPassword").attributes("disabled")).toBeDefined();

    await wrapper.find("#awsRegion").setValue("");

    expect(wrapper.vm.iamAuthInUse).toBe(false);
    expect(wrapper.find("#connectionPassword").attributes("disabled")).toBeUndefined();
  });

  it("resets credentials_extra when the technology changes", async () => {
    wrapper = await mountConnectionForm(
      mount,
      ConnectionsModalConnectionForm,
      rdsConnection({ credentials_extra: { aws_region: "us-east-1" } })
    );

    await wrapper.find("#connectionType").setValue("postgresql");

    expect(wrapper.vm.connectionLocal.credentials_extra).toEqual({});
    expect(wrapper.vm.isRdsPostgresql).toBe(false);
  });
});
