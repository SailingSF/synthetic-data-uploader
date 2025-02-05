import { useState } from "react";
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { useFetcher } from "@remix-run/react";
import {
  Page,
  Layout,
  Text,
  Card,
  Button,
  BlockStack,
  TextField,
  Banner,
  List,
  DataTable,
  Badge,
} from "@shopify/polaris";
import { TitleBar } from "@shopify/app-bridge-react";
import { authenticate } from "../shopify.server";

type OrderStatus = {
  financial: string;
  fulfillment: string;
};

type Order = {
  id: string;
  name: string;
  email: string;
  total: string;
  status: OrderStatus;
  items: number;
};

type FailedOrder = {
  email: string;
  items: number;
  error: string;
};

type ApiResponse = {
  success: boolean;
  message: string;
  items: Order[];
  failed_items?: FailedOrder[];
};

type FetcherData = {
  success: boolean;
  data: ApiResponse;
  error?: string;
};

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { session } = await authenticate.admin(request);
  return { accessToken: session.accessToken };
};

export const action = async ({ request }: ActionFunctionArgs) => {
  const { session } = await authenticate.admin(request);
  const formData = await request.formData();
  const action = formData.get("action");
  const count = formData.get("count");
  const dateRange = formData.get("dateRange");

  try {
    const endpoint = action === "preview" ? "/preview" :
                    action === "generate-orders" ? "/generate-orders" :
                    action === "generate-inventory" ? "/generate-inventory" :
                    action === "clear" ? "/clear-orders" :
                    "/reset-inventory";

    const response = await fetch(`http://localhost:8000${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        shop_url: session.shop,
        access_token: session.accessToken,
        num_items: parseInt(count as string) || 5,
        date_range_days: parseInt(dateRange as string) || 30
      }),
    });

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : "An error occurred" };
  }
};

export default function Index() {
  const fetcher = useFetcher<FetcherData>();
  const [count, setCount] = useState("5");
  const [dateRange, setDateRange] = useState("30");

  const isLoading = fetcher.state !== "idle";

  const renderOrdersTable = (orders: Order[]) => {
    const rows = orders.map((order) => [
      <Text as="span" variant="bodyMd">{order.name}</Text>,
      <Text as="span" variant="bodyMd">{order.email}</Text>,
      <Text as="span" variant="bodyMd">${order.total}</Text>,
      <Badge tone={order.status.financial === "PAID" ? "success" : "attention"}>
        {order.status.financial}
      </Badge>,
      <Badge tone={order.status.fulfillment === "FULFILLED" ? "success" : "attention"}>
        {order.status.fulfillment}
      </Badge>,
      <Text as="span" variant="bodyMd">{order.items}</Text>
    ]);

    return (
      <DataTable
        columnContentTypes={[
          'text',
          'text',
          'numeric',
          'text',
          'text',
          'numeric'
        ]}
        headings={[
          'Order',
          'Customer',
          'Total',
          'Payment',
          'Fulfillment',
          'Items'
        ]}
        rows={rows}
      />
    );
  };

  const renderResults = () => {
    if (!fetcher.data) return null;

    const { success, data, error } = fetcher.data;
    if (!success) {
      return (
        <Banner tone="critical">
          <Text as="p">Error: {error}</Text>
        </Banner>
      );
    }

    if (data.success === false) {
      return (
        <Banner tone="warning">
          <Text as="p">{data.message}</Text>
          {data.failed_items && data.failed_items.length > 0 && (
            <List type="bullet">
              {data.failed_items.map((item: FailedOrder, index: number) => (
                <List.Item key={index}>
                  {item.email} ({item.items} items) - {item.error}
                </List.Item>
              ))}
            </List>
          )}
        </Banner>
      );
    }

    return (
      <BlockStack gap="400">
        <Banner tone="success">
          <Text as="p">{data.message}</Text>
        </Banner>

        {data.items && data.items.length > 0 && (
          <Card>
            {renderOrdersTable(data.items)}
          </Card>
        )}
      </BlockStack>
    );
  };

  const handleAction = (action: string) => {
    fetcher.submit(
      { action, count, dateRange }, 
      { method: "POST" }
    );
  };

  return (
    <Page>
      <TitleBar title="Synthetic Data Generator" />
      <BlockStack gap="500">
        <Layout>
          <Layout.Section>
            <Card>
              <BlockStack gap="400">
                <Text as="h2" variant="headingMd">
                  Generate Synthetic Data
                </Text>

                <TextField
                  label="Number of items"
                  type="number"
                  value={count}
                  onChange={setCount}
                  autoComplete="off"
                  disabled={isLoading}
                />

                <TextField
                  label="Date range (days)"
                  type="number"
                  value={dateRange}
                  onChange={setDateRange}
                  autoComplete="off"
                  disabled={isLoading}
                />

                <BlockStack gap="200">
                  <Button
                    onClick={() => handleAction("preview")}
                    loading={isLoading && fetcher.formData?.get("action") === "preview"}
                    disabled={isLoading}
                  >
                    Preview Data
                  </Button>

                  <Button
                    onClick={() => handleAction("generate-orders")}
                    loading={isLoading && fetcher.formData?.get("action") === "generate-orders"}
                    disabled={isLoading}
                    variant="primary"
                  >
                    Generate Orders
                  </Button>

                  <Button
                    onClick={() => handleAction("generate-inventory")}
                    loading={isLoading && fetcher.formData?.get("action") === "generate-inventory"}
                    disabled={isLoading}
                  >
                    Generate Inventory
                  </Button>

                  <Button
                    onClick={() => handleAction("clear")}
                    loading={isLoading && fetcher.formData?.get("action") === "clear"}
                    disabled={isLoading}
                    tone="critical"
                  >
                    Clear Generated Orders
                  </Button>

                  <Button
                    onClick={() => handleAction("reset")}
                    loading={isLoading && fetcher.formData?.get("action") === "reset"}
                    disabled={isLoading}
                    tone="critical"
                  >
                    Reset Inventory
                  </Button>
                </BlockStack>

                {renderResults()}
              </BlockStack>
            </Card>
          </Layout.Section>
        </Layout>
      </BlockStack>
    </Page>
  );
}
